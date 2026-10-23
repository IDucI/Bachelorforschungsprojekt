import argparse
import csv
import random
import statistics
import time
from pathlib import Path

import chipwhisperer as cw

from board_test import (
    BAUDRATE,
    LESS_FQ_INV,
    LESS_GENERATOR_MONOMIAL_MUL,
    LESS_GENERATOR_SAMPLE,
    LESS_MONOMIAL_SAMPLE_PRIKEY,
    LESS_ROW_MUL3,
    PARAMETER_SETS,
    board_write_buffer,
    make_less,
    random_bytes,
    board_execute_subroutine,
    release_cdc_acm,
    serialize_positions,
    ss_send_cmd,
    ss_read_packet,
    wait_for_ack,
)

from run_board_test import (
    flash_firmware,
    get_hex_path,
)

BASE_DIR = Path(__file__).resolve().parent

RESULTS_DIR = BASE_DIR / "results"

OUTPUT_FILE = RESULTS_DIR / "runtime_measurement.csv"

REPETITIONS = 10

SUBROUTINES = (
    (
        "fq_inv",
        LESS_FQ_INV,
    ),
    (
        "row_mul3",
        LESS_ROW_MUL3,
    ),
    (
        "generator_sample",
        LESS_GENERATOR_SAMPLE,
    ),
    (
        "monomial_sample_prikey",
        LESS_MONOMIAL_SAMPLE_PRIKEY,
    ),
    (
        "generator_monomial_mul",
        LESS_GENERATOR_MONOMIAL_MUL,
    ),
)


def make_input(
    name,
    less,
    rng,
):
    """Generate input data for the selected LESS subroutine."""
    sub = less.subfunctions

    if name == "fq_inv":
        return bytes(
            [
                rng.randrange(
                    1,
                    sub.q,
                )
            ]
        )

    if name == "row_mul3":
        count = sub.row_values_count

        return bytes([rng.randrange(sub.q) for _ in range(2 * count)])

    if name == "generator_sample":
        return random_bytes(
            rng,
            sub.seed_length_bytes,
        )

    if name == "monomial_sample_prikey":
        return random_bytes(
            rng,
            sub.private_key_seed_length_bytes,
        )

    if name == "generator_monomial_mul":
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

        return bytes(generator) + bytes(coefficients) + serialize_positions(permutation)

    raise ValueError(name)


def connect_board():
    """Connect to the Pinata using ChipWhisperer and SimpleSerial2."""
    release_cdc_acm()
    scope = cw.scope()
    scope.default_setup()
    scope.io.clkout = 16e6
    time.sleep(0.2)
    target = cw.target(scope, cw.targets.SimpleSerial2)
    target.baud = BAUDRATE
    target.reset_comms()
    return scope, target


def measure_once(target, subroutine_id, input_data):
    """Execute a subroutine and read its DWT cycle count and CPU clock."""
    board_write_buffer(target, input_data)
    board_execute_subroutine(target, subroutine_id, timeout_ms=60000)

    ss_send_cmd(target, ord("c"), 0, b"")
    _, data = ss_read_packet(target, expected_cmd=ord("r"), expected_len=8)
    wait_for_ack(target)

    cycles = int.from_bytes(data[:4], "little")
    cpu_hz = int.from_bytes(data[4:], "little")
    if cycles == 0 or cpu_hz == 0:
        raise RuntimeError(f"Invalid DWT reading: cycles={cycles}, cpu_hz={cpu_hz}")
    return cycles, cpu_hz


def measure_category(category, base_seed):
    """Measure each supported subroutine ten times for one parameter set.
    Calculate cycle and runtime statistics from the DWT measurements."""
    less = make_less(category)
    scope = target = None
    rows = []
    try:
        scope, target = connect_board()
        for index, (name, subroutine_id) in enumerate(SUBROUTINES):
            if name == "generator_monomial_mul" and less.params.category in (3, 5):
                print(f"{category}: {name}: unsupported on STM32 (SKIP)")
                continue

            cycles = []
            cpu_rates = []
            for repetition in range(REPETITIONS):
                rng = random.Random(
                    (base_seed + index * 1000 + repetition) & 0xFFFFFFFF
                )
                input_data = make_input(name, less, rng)
                count, cpu_hz = measure_once(target, subroutine_id, input_data)
                cycles.append(count)
                cpu_rates.append(cpu_hz)

            if len(set(cpu_rates)) != 1:
                raise RuntimeError(
                    f"CPU clock changed during {category}/{name}: {cpu_rates}"
                )
            # Convert CPU cycles to microseconds using the reported clock frequency.
            microseconds = [count * 1e6 / cpu_rates[0] for count in cycles]
            rows.append(
                {
                    "category": category,
                    "subroutine": name,
                    "repetitions": REPETITIONS,
                    "cpu_clock_hz": cpu_rates[0],
                    "mean_cycles": f"{statistics.mean(cycles):.2f}",
                    "median_cycles": statistics.median(cycles),
                    "min_cycles": min(cycles),
                    "max_cycles": max(cycles),
                    "mean_us": f"{statistics.mean(microseconds):.3f}",
                    "median_us": f"{statistics.median(microseconds):.3f}",
                    "min_us": f"{min(microseconds):.3f}",
                    "max_us": f"{max(microseconds):.3f}",
                    "stdev_us": f"{statistics.pstdev(microseconds):.3f}",
                }
            )
            print(f"{category:<10} {name:<28} {statistics.mean(cycles):>12.2f} cycles")
    finally:
        if target is not None:
            target.dis()
        if scope is not None:
            scope.dis()
    return rows


def write_results(rows):
    """Write the collected runtime measurements to a CSV file."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    """Select firmware variants, run DWT measurements and save the results."""
    parser = argparse.ArgumentParser(
        description="Measure LESS subroutine CPU cycles using STM32F4 DWT CYCCNT."
    )
    parser.add_argument(
        "category",
        nargs="?",
        choices=PARAMETER_SETS,
        help="one variant, or omit to measure all eight",
    )
    parser.add_argument(
        "--no-flash",
        action="store_true",
        help="use the currently flashed firmware (one variant only)",
    )
    parser.add_argument("--seed", type=int, default=123456)
    args = parser.parse_args()

    categories = (args.category,) if args.category else tuple(PARAMETER_SETS)
    if args.no_flash and len(categories) != 1:
        parser.error("--no-flash requires one explicit category")

    rows = []
    for category in categories:
        if not args.no_flash:
            hex_path = get_hex_path(category)
            if not hex_path.is_file():
                raise FileNotFoundError(
                    f"Missing {hex_path.name}; compile firmware first"
                )
            if not flash_firmware(hex_path):
                raise RuntimeError(f"Flashing {category} failed")
        rows.extend(measure_category(category, args.seed))

    if not rows:
        raise RuntimeError("No DWT measurements were produced")
    write_results(rows)
    print(f"Runtime results written to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
