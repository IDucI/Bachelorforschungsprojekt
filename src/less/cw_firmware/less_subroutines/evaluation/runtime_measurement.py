import argparse
import csv
import random
import statistics
import sys
from pathlib import Path

import chipwhisperer as cw

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
LIBLESS_DIR = PROJECT_DIR.parent.parent / "libless"

if str(LIBLESS_DIR) not in sys.path:
    sys.path.insert(0, str(LIBLESS_DIR))

from board_test import (
    PARAMETER_SETS,
    BAUDRATE,
    release_cdc_acm,
    board_run_subroutine,
    create_reference_cases,
    make_less,
)

from run_board_test import get_hex_path, flash_firmware

REPETITIONS = 10
RESULTS_DIR = BASE_DIR / "results"
OUTPUT_FILE = RESULTS_DIR / "runtime_measurement.csv"

FAIL_ON_MEASUREMENT_ERROR = False


def read_cycles(target):
    """Read the last DWT cycle count and STM32 CPU clock frequency."""
    target.send_cmd(ord("c"), 0, b"")

    response = target.simpleserial_read("r", 8, timeout=5000, ack=False)

    if response is None or len(response) != 8:
        raise TimeoutError("Missing or incomplete cycle response")

    status = target.simpleserial_wait_ack(timeout=5000)

    if status is None or len(status) != 1 or status[0] != 0:
        raise RuntimeError(f"Invalid cycle response acknowledgement: {status!r}")

    cycles = int.from_bytes(response[:4], "little")
    cpu_hz = int.from_bytes(response[4:8], "little")

    if cycles <= 0 or cpu_hz <= 0:
        raise RuntimeError(
            f"Invalid cycle count or CPU clock: {cycles} cycles, {cpu_hz} Hz"
        )

    return cycles, cpu_hz


def execute_once(target, case):
    """Execute a subroutine and verify its output before reading cycles."""
    actual_output = board_run_subroutine(
        target, case["id"], case["input"], case["output_length"]
    )

    if actual_output != case["expected_output"]:
        raise AssertionError(f"{case['name']}: output differs from LESS reference")

    return read_cycles(target)


def connect_board():
    """Connect to the Pinata using ChipWhisperer and SimpleSerial2."""
    release_cdc_acm()
    scope = cw.scope()
    target = None

    try:
        scope.default_setup()
        scope.io.clkout = 16e6

        target = cw.target(scope, cw.targets.SimpleSerial2)
        target.baud = BAUDRATE
        target.reset_comms()

        return scope, target

    except Exception:
        if target is not None:
            try:
                target.dis()
            except Exception:
                pass
        scope.dis()
        raise


def measure_case(target, case, repetitions):
    """Repeat the measurement and calculate runtime statistics."""
    cycles_values = []
    cpu_values = []
    errors = []

    for repetition in range(repetitions):
        try:
            cycles, cpu_hz = execute_once(target, case)

            cycles_values.append(cycles)
            cpu_values.append(cpu_hz)

            print(
                f"    Run {repetition + 1}/{repetitions}: "
                f"{cycles} cycles, {cycles / cpu_hz * 1e6:.4f} us"
            )

        except Exception as exc:
            message = (
                f"{case['name']} repetition {repetition + 1}: "
                f"{type(exc).__name__}: {exc}"
            )
            print(f"    ERROR: {message}")
            errors.append(message)

            try:
                target.reset_comms()
            except Exception:
                pass

            if FAIL_ON_MEASUREMENT_ERROR:
                raise

    if not cycles_values:
        return {
            "repetitions_requested": repetitions,
            "repetitions_completed": 0,
            "cpu_clock_hz": "",
            "mean_cycles": "",
            "median_cycles": "",
            "min_cycles": "",
            "max_cycles": "",
            "mean_us": "",
            "median_us": "",
            "min_us": "",
            "max_us": "",
            "stdev_us": "",
            "error": " | ".join(errors),
        }

    if len(set(cpu_values)) != 1:
        raise RuntimeError(f"CPU clock changed during {case['name']}: {cpu_values}")

    cpu_hz = cpu_values[0]
    runtime_us = [cycles / cpu_hz * 1_000_000 for cycles in cycles_values]

    return {
        "repetitions_requested": repetitions,
        "repetitions_completed": len(cycles_values),
        "cpu_clock_hz": cpu_hz,
        "mean_cycles": statistics.mean(cycles_values),
        "median_cycles": statistics.median(cycles_values),
        "min_cycles": min(cycles_values),
        "max_cycles": max(cycles_values),
        "mean_us": statistics.mean(runtime_us),
        "median_us": statistics.median(runtime_us),
        "min_us": min(runtime_us),
        "max_us": max(runtime_us),
        "stdev_us": statistics.stdev(runtime_us) if len(runtime_us) > 1 else 0.0,
        "error": " | ".join(errors),
    }


def write_results(rows):
    """Write the collected runtime measurements to a CSV file."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    fields = [
        "family",
        "category",
        "variant",
        "subroutine",
        "repetitions_requested",
        "repetitions_completed",
        "error",
        "cpu_clock_hz",
        "mean_cycles",
        "median_cycles",
        "min_cycles",
        "max_cycles",
        "mean_us",
        "median_us",
        "min_us",
        "max_us",
        "stdev_us",
    ]

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()

        for row in rows:
            writer.writerow(
                {
                    **{
                        name: row[name]
                        for name in fields
                        if name
                        not in ("mean_us", "median_us", "min_us", "max_us", "stdev_us")
                    },
                    **{
                        name: f"{row[name]:.3f}" if row[name] != "" else ""
                        for name in (
                            "mean_us",
                            "median_us",
                            "min_us",
                            "max_us",
                            "stdev_us",
                        )
                    },
                }
            )

    print(f"\nCSV results saved to: {OUTPUT_FILE}")


def main():
    """Select firmware variants, run DWT measurements and save the results."""
    parser = argparse.ArgumentParser(
        description="Measure LESS subroutine runtimes on the ChipWhisperer."
    )
    parser.add_argument("category", nargs="?", choices=tuple(PARAMETER_SETS))
    parser.add_argument(
        "--no-flash",
        action="store_true",
        help="Use firmware already flashed on the board.",
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="Seed for reference inputs."
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=REPETITIONS,
        help="Number of runtime measurements per subroutine.",
    )

    args = parser.parse_args()

    if args.no_flash and args.category is None:
        parser.error("--no-flash requires one explicit configuration.")

    if args.repetitions < 1:
        parser.error("--repetitions must be at least 1.")

    configurations = [args.category] if args.category else list(PARAMETER_SETS)
    seed = (
        args.seed
        if args.seed is not None
        else random.SystemRandom().randint(0, 2**32 - 1)
    )

    print("=" * 70)
    print("LESS Runtime Measurement")
    print("=" * 70)
    print(f"Configurations: {len(configurations)}")
    print(f"Repetitions per subroutine: {args.repetitions}")
    print(f"Random seed: {seed}")
    print(f"Flash firmware: {not args.no_flash}")

    rows = []
    overall_failed = False

    for index, category in enumerate(configurations, start=1):
        print("\n" + "=" * 70)
        print(f"Configuration {index}/{len(configurations)}: {category}")
        print("=" * 70)

        if not args.no_flash:
            hex_path = get_hex_path(category)
            if not hex_path.is_file():
                print(f"ERROR: Firmware not found: {hex_path}")
                overall_failed = True
                continue

            if not flash_firmware(hex_path):
                print(f"ERROR: Firmware flashing failed: {hex_path}")
                overall_failed = True
                continue

        less = make_less(category)

        config_seed = seed + configurations.index(category) * 100000
        rng = random.Random(config_seed)
        cases = create_reference_cases(less, rng)

        scope, target = connect_board()

        try:
            for case in cases:
                print(
                    f"\n  {case['name']} "
                    f"(ID 0x{case['id']:02X}, "
                    f"input={len(case['input'])} bytes, "
                    f"output={case['output_length']} bytes)"
                )

                measurement = measure_case(target, case, args.repetitions)

                if measurement["repetitions_completed"] == 0:
                    overall_failed = True

                rows.append(
                    {
                        "family": "LESS",
                        "category": category,
                        "variant": "",
                        "subroutine": case["name"],
                        **measurement,
                    }
                )

        finally:
            try:
                target.dis()
            finally:
                scope.dis()

        write_results(rows)

    if rows:
        write_results(rows)

    print("\n" + "=" * 70)
    print("Runtime measurement finished.")
    print(f"Results: {OUTPUT_FILE}")
    print("=" * 70)

    return 1 if overall_failed else 0


if __name__ == "__main__":
    sys.exit(main())
