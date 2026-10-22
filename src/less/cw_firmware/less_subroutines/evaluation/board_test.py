import argparse
import csv
import random
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import chipwhisperer as cw

EVALUATION_DIR = Path(__file__).resolve().parent
FIRMWARE_DIR = EVALUATION_DIR.parent
LIBLESS_DIR = FIRMWARE_DIR.parent.parent / "libless"
BUILD_DIR = LIBLESS_DIR / "build"
RESULTS_CSV = EVALUATION_DIR / "board_test_details.csv"

if str(LIBLESS_DIR) not in sys.path:
    sys.path.insert(0, str(LIBLESS_DIR))

from less import Less

PARAMETER_SETS = {
    "toy": (None, None),
    "cat1_192": (1, 192),
    "cat1_68": (1, 68),
    "cat1_45": (1, 45),
    "cat3_220": (3, 220),
    "cat3_102": (3, 102),
    "cat5_345": (5, 345),
    "cat5_137": (5, 137),
}

BAUDRATE = 230400
INPUT_CHUNK_SIZE = 160
OUTPUT_CHUNK_SIZE = 160
ROUNDS_PER_SUBROUTINE = 5

LESS_FQ_INV = 0x03
LESS_ROW_MUL3 = 0x04
LESS_GENERATOR_SAMPLE = 0x05
LESS_MONOMIAL_SAMPLE_PRIKEY = 0x06
LESS_GENERATOR_MONOMIAL_MUL = 0x07


def ss_send_cmd(target, cmd: int, scmd: int, data: bytes = b"") -> None:
    data = bytes(data)

    if len(data) > 0xFF:
        raise ValueError("SimpleSerial payload exceeds 255 bytes")

    target.send_cmd(
        cmd,
        scmd,
        bytearray(data),
    )


def ss_read_packet(
    target,
    expected_cmd: int | None = None,
    expected_len: int | None = None,
    timeout_ms: int = 5000,
):
    packet = target.read_cmd(
        cmd=expected_cmd,
        pay_len=expected_len,
        timeout=timeout_ms,
    )

    if packet is None:
        raise TimeoutError("Timeout waiting for SimpleSerial response")

    raw = bytes(packet)

    if len(raw) < 5:
        raise RuntimeError("SimpleSerial response too short")

    cmd = raw[1]
    data_len = raw[2]
    data = raw[3:-2]

    if len(data) != data_len:
        raise RuntimeError(
            f"Invalid SimpleSerial payload length: "
            f"header says {data_len}, got {len(data)}"
        )

    if expected_cmd is not None and cmd != expected_cmd:
        if cmd == ord("e") and len(data) == 1:
            if data[0] != 0:
                raise RuntimeError(f"STM32 returned SimpleSerial error 0x{data[0]:02X}")

            raise RuntimeError("Received SimpleSerial ACK before the expected response")

        raise RuntimeError(
            f"Expected SimpleSerial command 0x{expected_cmd:02X}, " f"got 0x{cmd:02X}"
        )

    if expected_len is not None and len(data) != expected_len:
        raise RuntimeError(
            f"Expected SimpleSerial payload length " f"{expected_len}, got {len(data)}"
        )

    return cmd, data


def wait_for_ack(target, timeout_ms: int = 5000) -> None:
    _, data = ss_read_packet(
        target,
        expected_cmd=ord("e"),
        expected_len=1,
        timeout_ms=timeout_ms,
    )

    if data[0] != 0:
        raise RuntimeError(f"STM32 returned SimpleSerial error 0x{data[0]:02X}")


def release_cdc_acm() -> None:
    subprocess.run(
        ["sudo", "modprobe", "-r", "cdc_acm"],
        check=False,
    )


def board_write_buffer(target, data: bytes) -> None:
    data = bytes(data)

    if not data:
        raise ValueError("Cannot upload an empty input buffer")

    for chunk_index, offset in enumerate(range(0, len(data), INPUT_CHUNK_SIZE)):
        if chunk_index > 0xFF:
            raise ValueError("Input requires more than 256 chunks")

        chunk = data[offset : offset + INPUT_CHUNK_SIZE]

        ss_send_cmd(
            target,
            ord("s"),
            chunk_index,
            chunk,
        )

        wait_for_ack(target)


def board_execute_subroutine(
    target,
    subroutine_id: int,
    timeout_ms: int = 30000,
) -> None:
    ss_send_cmd(
        target,
        ord("b"),
        subroutine_id,
        b"",
    )

    wait_for_ack(
        target,
        timeout_ms=timeout_ms,
    )


def board_read_result(
    target,
    output_len: int,
    timeout_ms: int = 5000,
) -> bytes:
    output = bytearray()

    number_of_chunks = (output_len + OUTPUT_CHUNK_SIZE - 1) // OUTPUT_CHUNK_SIZE

    for chunk_index in range(number_of_chunks):
        if chunk_index > 0xFFFF:
            raise ValueError("Output requires more than 65536 chunks")

        request = bytes(
            [
                chunk_index & 0xFF,
                (chunk_index >> 8) & 0xFF,
            ]
        )

        ss_send_cmd(
            target,
            ord("g"),
            0,
            request,
        )

        cmd, data = ss_read_packet(
            target,
            timeout_ms=timeout_ms,
        )

        if cmd == ord("e"):
            error = data[0] if len(data) == 1 else None

            raise RuntimeError(
                f"Board rejected output chunk " f"{chunk_index}: error={error!r}"
            )

        if cmd != ord("r"):
            raise RuntimeError(f"Expected result command 'r', " f"got 0x{cmd:02X}")

        expected_len = min(
            OUTPUT_CHUNK_SIZE,
            output_len - chunk_index * OUTPUT_CHUNK_SIZE,
        )

        if len(data) != expected_len:
            raise RuntimeError(
                f"Output chunk {chunk_index}: "
                f"expected {expected_len} bytes, "
                f"got {len(data)}"
            )

        output.extend(data)

        wait_for_ack(
            target,
            timeout_ms=timeout_ms,
        )

    return bytes(output)


def board_run_subroutine(
    target,
    subroutine_id: int,
    input_data: bytes,
    output_len: int,
) -> bytes:
    board_write_buffer(
        target,
        input_data,
    )

    board_execute_subroutine(
        target,
        subroutine_id,
    )

    return board_read_result(
        target,
        output_len,
    )


def random_bytes(rng, length: int) -> bytes:
    return bytes(rng.randrange(256) for _ in range(length))


def serialize_positions(values) -> bytes:
    output = bytearray()

    for value in values:
        if value < 0 or value > 0xFFFF:
            raise ValueError("POSITION_T value outside uint16 range")

        output.append(value & 0xFF)

        output.append((value >> 8) & 0xFF)

    return bytes(output)


def compare(
    name: str,
    expected: bytes,
    actual: bytes,
) -> None:
    if expected == actual:
        return

    common_length = min(
        len(expected),
        len(actual),
    )

    first_difference = next(
        (index for index in range(common_length) if expected[index] != actual[index]),
        None,
    )

    if first_difference is None:
        detail = (
            f"different lengths: " f"expected {len(expected)}, " f"got {len(actual)}"
        )
    else:
        detail = (
            f"first difference at byte "
            f"{first_difference}: "
            f"expected "
            f"{expected[first_difference]}, "
            f"got {actual[first_difference]}"
        )

    raise AssertionError(f"{name}: {detail}")


def test_fq_inv(
    target,
    less,
    rng,
) -> None:
    value = rng.randrange(
        1,
        less.subfunctions.q,
    )

    expected = bytes([less.subfunctions.fq_inv(value)])

    actual = board_run_subroutine(
        target,
        LESS_FQ_INV,
        bytes([value]),
        len(expected),
    )

    compare(
        "fq_inv",
        expected,
        actual,
    )


def test_row_mul3(
    target,
    less,
    rng,
) -> None:
    count = less.subfunctions.row_values_count

    q = less.subfunctions.q

    in1 = [rng.randrange(q) for _ in range(count)]

    in2 = [rng.randrange(q) for _ in range(count)]

    expected = bytes(
        less.subfunctions.row_mul3(
            in1,
            in2,
        )
    )

    actual = board_run_subroutine(
        target,
        LESS_ROW_MUL3,
        bytes(in1) + bytes(in2),
        len(expected),
    )

    compare(
        "row_mul3",
        expected,
        actual,
    )


def test_generator_sample(
    target,
    less,
    rng,
) -> None:
    seed = random_bytes(
        rng,
        less.subfunctions.seed_length_bytes,
    )

    values, positions = less.subfunctions.generator_sample(seed)

    expected = bytes(values) + serialize_positions(positions)

    actual = board_run_subroutine(
        target,
        LESS_GENERATOR_SAMPLE,
        seed,
        len(expected),
    )

    compare(
        "generator_sample",
        expected,
        actual,
    )


def test_monomial_sample_prikey(
    target,
    less,
    rng,
) -> None:
    seed = random_bytes(
        rng,
        less.subfunctions.private_key_seed_length_bytes,
    )

    coefficients, permutation = less.subfunctions.monomial_sample_prikey(seed)

    expected = bytes(coefficients) + serialize_positions(permutation)

    actual = board_run_subroutine(
        target,
        LESS_MONOMIAL_SAMPLE_PRIKEY,
        seed,
        len(expected),
    )

    compare(
        "monomial_sample_prikey",
        expected,
        actual,
    )


def test_generator_monomial_mul(
    target,
    less,
    rng,
) -> None:
    sub = less.subfunctions

    generator = [rng.randrange(sub.q) for _ in range(sub.generator_values_count)]

    coefficients = [
        rng.randrange(
            1,
            sub.q,
        )
        for _ in range(sub.n)
    ]

    permutation = list(range(sub.n))

    rng.shuffle(permutation)

    expected = bytes(
        sub.generator_monomial_mul(
            generator,
            coefficients,
            permutation,
        )
    )

    input_data = (
        bytes(generator) + bytes(coefficients) + serialize_positions(permutation)
    )

    actual = board_run_subroutine(
        target,
        LESS_GENERATOR_MONOMIAL_MUL,
        input_data,
        len(expected),
    )

    compare(
        "generator_monomial_mul",
        expected,
        actual,
    )


COMMON_TESTS = [
    (
        "fq_inv",
        test_fq_inv,
    ),
    (
        "row_mul3",
        test_row_mul3,
    ),
    (
        "generator_sample",
        test_generator_sample,
    ),
    (
        "monomial_sample_prikey",
        test_monomial_sample_prikey,
    ),
]


def make_less(
    category_name: str,
) -> Less:
    category, target = PARAMETER_SETS[category_name]

    return Less(
        path=str(BUILD_DIR),
        category=category,
        target=target,
    )


def log_test_result(
    category: str,
    subroutine: str,
    round_number: int | None,
    base_seed: int,
    test_seed: int | None,
    status: str,
    error: str = "",
) -> None:
    needs_header = not RESULTS_CSV.exists() or RESULTS_CSV.stat().st_size == 0

    with RESULTS_CSV.open("a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        if needs_header:
            writer.writerow(
                [
                    "timestamp",
                    "category",
                    "subroutine",
                    "round",
                    "base_seed",
                    "test_seed",
                    "status",
                    "error",
                ]
            )

        writer.writerow(
            [
                datetime.now().astimezone().isoformat(timespec="seconds"),
                category,
                subroutine,
                round_number,
                base_seed,
                test_seed,
                status,
                error,
            ]
        )


def run_tests(
    target,
    less,
    category_name: str,
    base_seed: int,
) -> bool:
    tests = list(COMMON_TESTS)

    if less.params.category in {
        None,
        1,
    }:
        tests.append(
            (
                "generator_monomial_mul",
                test_generator_monomial_mul,
            )
        )

    total = len(tests) * ROUNDS_PER_SUBROUTINE

    passed = 0

    print()
    print("=" * 64)

    print(f" LESS board/reference tests: " f"{category_name}")

    print("=" * 64)

    print(f"Rounds per subroutine : " f"{ROUNDS_PER_SUBROUTINE}")

    print(f"Total board tests     : " f"{total}")

    print(f"Base random seed      : " f"{base_seed}")

    print()

    for test_number, (
        name,
        test_function,
    ) in enumerate(
        tests,
        start=1,
    ):
        print(
            f"[{test_number:02d}/" f"{len(tests):02d}] " f"{name:<30}",
            end="",
            flush=True,
        )

        for round_number in range(
            1,
            ROUNDS_PER_SUBROUTINE + 1,
        ):
            seed = (base_seed + test_number * 1000 + round_number) & 0xFFFFFFFF

            rng = random.Random(seed)

            try:
                test_function(
                    target,
                    less,
                    rng,
                )

            except Exception as exc:
                log_test_result(
                    category_name,
                    name,
                    round_number,
                    base_seed,
                    seed,
                    "Fail",
                    f"{type(exc).__name__}: {exc}",
                )

                print("Fail")

                print()

                print("=" * 64)
                print("TEST FAILURE")
                print("=" * 64)

                print(f"Category   : " f"{category_name}")

                print(f"Subroutine : " f"{name}")

                print(f"Round      : " f"{round_number}/" f"{ROUNDS_PER_SUBROUTINE}")

                print(f"Seed       : " f"{seed}")

                print(f"Exception  : " f"{type(exc).__name__}: " f"{exc}")

                print("=" * 64)

                return False

            log_test_result(
                category_name,
                name,
                round_number,
                base_seed,
                seed,
                "Pass",
            )

            passed += 1

        print(f"Pass " f"({ROUNDS_PER_SUBROUTINE}/" f"{ROUNDS_PER_SUBROUTINE})")

    if less.params.category in {
        3,
        5,
    }:

        log_test_result(
            category_name,
            "generator_monomial_mul",
            None,
            base_seed,
            None,
            "Skip",
            "STM32F4 memory budget",
        )

        print(
            "[SKIP] generator_monomial_mul: "
            "disabled for this firmware category "
            "because of the STM32F4 memory budget"
        )

    print()
    print("=" * 64)

    print(f"{passed}/{total} " f"supported board tests passed")

    print("=" * 64)

    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare LESS subroutine results "
            "from the Piñata against the "
            "host-side libless reference wrapper."
        )
    )

    parser.add_argument(
        "category",
        choices=PARAMETER_SETS,
        help=("firmware category currently " "flashed on the Piñata"),
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help=("optional base seed for " "reproducible random tests"),
    )

    args = parser.parse_args()

    base_seed = (
        args.seed
        if args.seed is not None
        else random.SystemRandom().randint(
            0,
            2**32 - 1,
        )
    )

    print()
    print("=" * 64)
    print(" LESS Board Reference Test")
    print("=" * 64)

    print(f"Category    : " f"{args.category}")

    print(f"Random seed : " f"{base_seed}")

    try:
        less = make_less(args.category)

    except Exception as exc:
        print()

        print(
            "Could not load the matching "
            "host-side libless build: "
            f"{type(exc).__name__}: {exc}"
        )

        print("Build libless first from " "src/less/libless with `make`.")

        return 1

    scope = None
    target = None

    try:
        release_cdc_acm()

        scope = cw.scope()

        scope.default_setup()

        scope.io.clkout = 15e6

        time.sleep(0.2)

        target = cw.target(
            scope,
            cw.targets.SimpleSerial2,
        )

        target.baud = BAUDRATE

        target.reset_comms()

        if run_tests(
            target,
            less,
            args.category,
            base_seed,
        ):
            print("Final result: Pass")

            return 0

        print("Final result: Fail")

        return 1

    except Exception as exc:
        print()

        print("=" * 64)
        print("BOARD TEST EXCEPTION")
        print("=" * 64)

        print(f"{type(exc).__name__}: " f"{exc}")

        print("=" * 64)

        return 1

    finally:
        if target is not None:
            try:
                target.dis()
            except Exception:
                pass

        if scope is not None:
            try:
                scope.dis()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
