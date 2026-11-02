import argparse
import random
import subprocess
import sys
import time
from pathlib import Path

import chipwhisperer as cw

EVALUATION_DIR = Path(__file__).resolve().parent
FIRMWARE_DIR = EVALUATION_DIR.parent
LIBLESS_DIR = FIRMWARE_DIR.parent.parent / "libless"
BUILD_DIR = LIBLESS_DIR / "build"

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
ROUNDS_PER_SUBROUTINE = 1

LESS_FQ_INV = 0x03
LESS_ROW_MUL3 = 0x04
LESS_GENERATOR_SAMPLE = 0x05
LESS_MONOMIAL_SAMPLE_PRIKEY = 0x06
LESS_GENERATOR_MONOMIAL_MUL = 0x07


def release_cdc_acm() -> None:
    """Release the Linux CDC-ACM driver before connecting to the board."""
    subprocess.run(
        ["sudo", "modprobe", "-r", "cdc_acm"],
        check=False,
    )


def board_write_buffer(target, data: bytes) -> None:
    """Write input data to the STM32 buffer in 160-byte chunks."""
    data = bytes(data)

    if not data:
        raise ValueError("Cannot upload an empty input buffer")

    for chunk_index, offset in enumerate(range(0, len(data), INPUT_CHUNK_SIZE)):
        if chunk_index > 0xFF:
            raise ValueError("Input requires more than 256 chunks")

        chunk = data[offset : offset + INPUT_CHUNK_SIZE]
        target.send_cmd(ord("s"), chunk_index, bytearray(chunk))

        status = target.simpleserial_wait_ack(timeout=5000)
        if status is None or len(status) != 1 or status[0] != 0:
            raise RuntimeError(f"Input chunk {chunk_index}: invalid ACK {status!r}")


def board_execute_subroutine(
    target,
    subroutine_id: int,
    timeout_ms: int = 30000,
) -> None:
    """Execute the selected subroutine and wait for its acknowledgement."""
    target.send_cmd(ord("b"), subroutine_id, bytearray())

    status = target.simpleserial_wait_ack(timeout=timeout_ms)
    if status is None or len(status) != 1 or status[0] != 0:
        raise RuntimeError(f"Subroutine 0x{subroutine_id:02X}: invalid ACK {status!r}")


def board_read_result(
    target,
    output_len: int,
    timeout_ms: int = 5000,
) -> bytes:
    """Read the subroutine result from the board in 160-byte chunks."""
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

        target.send_cmd(ord("g"), 0, bytearray(request))

        expected_len = min(
            OUTPUT_CHUNK_SIZE,
            output_len - chunk_index * OUTPUT_CHUNK_SIZE,
        )

        data = target.simpleserial_read(
            "r",
            expected_len,
            timeout=timeout_ms,
            ack=False,
        )

        if data is None:
            raise TimeoutError(f"Timeout waiting for output chunk {chunk_index}")

        if len(data) != expected_len:
            raise RuntimeError(
                f"Output chunk {chunk_index}: expected {expected_len} bytes, "
                f"got {len(data)}"
            )

        status = target.simpleserial_wait_ack(timeout=timeout_ms)
        if status is None or len(status) != 1 or status[0] != 0:
            raise RuntimeError(f"Output chunk {chunk_index}: invalid ACK {status!r}")

        output.extend(data)

    return bytes(output)


def board_run_subroutine(
    target,
    subroutine_id: int,
    input_data: bytes,
    output_len: int,
) -> bytes:
    """Upload input data, execute the subroutine and return its result."""
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
    """Generate random bytes using the provided random generator."""
    return bytes(rng.randrange(256) for _ in range(length))


def serialize_positions(values) -> bytes:
    """Encode 16-bit positions as little-endian bytes."""
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
    """Compare the board output with the reference result.
    Report the first differing byte or a length mismatch."""
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


def create_reference_cases(less, rng):
    """Generate inputs and expected outputs for the selected subroutines."""

    sub = less.subfunctions
    compressed_sk = random_bytes(rng, sub.private_key_seed_length_bytes)
    keygen = less.calculation.keygen(compressed_sk)

    cases = []

    def add(name, subroutine_id, input_data, output_data):
        cases.append(
            {
                "name": name,
                "id": subroutine_id,
                "input": bytes(input_data),
                "expected_output": bytes(output_data),
                "output_length": len(output_data),
            }
        )

    inv = keygen.fq_inv
    add(
        "fq_inv",
        LESS_FQ_INV,
        bytes([inv.value]),
        bytes([inv.inverse]),
    )

    count = sub.row_values_count
    in1 = [rng.randrange(sub.q) for _ in range(count)]
    in2 = [rng.randrange(sub.q) for _ in range(count)]
    result = sub.row_mul3(in1, in2)

    add(
        "row_mul3",
        LESS_ROW_MUL3,
        bytes(in1) + bytes(in2),
        result,
    )

    sample = keygen.generator_sample
    add(
        "generator_sample",
        LESS_GENERATOR_SAMPLE,
        sample.seed,
        sample.values + serialize_positions(sample.positions),
    )

    monomial = keygen.monomial_sample_prikey
    add(
        "monomial_sample_prikey",
        LESS_MONOMIAL_SAMPLE_PRIKEY,
        monomial.seed,
        monomial.coefficients + serialize_positions(monomial.permutation),
    )

    if less.params.category in (None, 1):
        multiplication = keygen.generator_monomial_mul

        add(
            "generator_monomial_mul",
            LESS_GENERATOR_MONOMIAL_MUL,
            multiplication.generator
            + multiplication.coefficients
            + serialize_positions(multiplication.permutation),
            multiplication.result,
        )

    return cases


def make_less(
    category_name: str,
) -> Less:
    """Load the host-side LESS library for the selected parameter set."""
    category, target = PARAMETER_SETS[category_name]

    return Less(
        path=str(BUILD_DIR),
        category=category,
        target=target,
    )



def run_tests(
    target,
    less,
    category_name: str,
    base_seed: int,
) -> bool:
    """Run the supported subroutine tests for one firmware variant.
    Compare each board result with the host reference implementation."""
    names = [
        "fq_inv",
        "row_mul3",
        "generator_sample",
        "monomial_sample_prikey",
    ]

    if less.params.category in {
        None,
        1,
    }:
        names.append("generator_monomial_mul")

    total = len(names) * ROUNDS_PER_SUBROUTINE
    passed = 0
    rounds = {}

    print()
    print("=" * 64)

    print(f" LESS board/reference tests: " f"{category_name}")

    print("=" * 64)

    print(f"Rounds per subroutine : " f"{ROUNDS_PER_SUBROUTINE}")

    print(f"Total board tests     : " f"{total}")

    print(f"Base random seed      : " f"{base_seed}")

    print()

    for test_number, name in enumerate(names, start=1):
        print(
            f"[{test_number:02d}/" f"{len(names):02d}] " f"{name:<30}",
            end="",
            flush=True,
        )

        for round_number in range(1, ROUNDS_PER_SUBROUTINE + 1):
            seed = (base_seed + round_number) & 0xFFFFFFFF

            try:
                if round_number not in rounds:
                    cases = create_reference_cases(less, random.Random(seed))
                    rounds[round_number] = {
                        case["name"]: case for case in cases
                    }

                case = rounds[round_number][name]

                actual = board_run_subroutine(
                    target,
                    case["id"],
                    case["input"],
                    case["output_length"],
                )

                compare(name, case["expected_output"], actual)

            except Exception as exc:

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


            passed += 1

        print(f"Pass " f"({ROUNDS_PER_SUBROUTINE}/" f"{ROUNDS_PER_SUBROUTINE})")

    if less.params.category in {
        3,
        5,
    }:


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
    """Connect to the board, run the selected tests and report the result."""
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

        scope.io.clkout = 16e6

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
