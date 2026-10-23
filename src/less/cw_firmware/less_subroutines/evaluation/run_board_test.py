import argparse
import subprocess
import sys
import time
from pathlib import Path
import csv
import random
from datetime import datetime

import chipwhisperer as cw

EVALUATION_DIR = Path(__file__).resolve().parent
FIRMWARE_DIR = EVALUATION_DIR.parent
BOARD_TEST = EVALUATION_DIR / "board_test.py"
RESULTS_CSV = EVALUATION_DIR / "board_test_results.csv"

CATEGORIES = (
    "toy",
    "cat1_192",
    "cat1_68",
    "cat1_45",
    "cat3_220",
    "cat3_102",
    "cat5_345",
    "cat5_137",
)

PROGRAM_BAUDRATE = 230400


def release_cdc_acm() -> None:
    """Release the Linux CDC-ACM driver before connecting to the board."""
    subprocess.run(
        ["sudo", "modprobe", "-r", "cdc_acm"],
        check=False,
    )


def initialize_results_csv() -> None:
    """Create a new CSV summary with the board test result columns."""
    with RESULTS_CSV.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "timestamp",
                "category",
                "base_seed",
                "hex_exists",
                "flash_passed",
                "board_test_passed",
                "error",
            ]
        )


def log_result(
    category: str,
    seed: int,
    hex_exists: bool,
    flash_passed: bool,
    board_test_passed: bool,
    error: str = "",
) -> None:
    """Append the firmware and board test status to the CSV summary."""
    with RESULTS_CSV.open("a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                datetime.now().astimezone().isoformat(timespec="seconds"),
                category,
                seed,
                hex_exists,
                flash_passed,
                board_test_passed,
                error,
            ]
        )


def get_hex_path(
    category: str,
) -> Path:
    """Return the expected firmware HEX path for a parameter set."""
    return FIRMWARE_DIR / (f"less_subroutines_" f"{category}-PINATA.hex")


def flash_firmware(
    hex_path: Path,
) -> bool:
    """Program the STM32 with the selected firmware HEX file."""
    scope = None

    try:
        release_cdc_acm()

        scope = cw.scope()

        scope.default_setup()

        scope.io.clkout = 16e6

        time.sleep(0.2)

        cw.program_target(
            scope,
            cw.programmers.STM32FProgrammer,
            str(hex_path),
            baud=PROGRAM_BAUDRATE,
        )

        return True

    except Exception as exc:
        print(f"Flash failed: " f"{type(exc).__name__}: " f"{exc}")

        return False

    finally:
        if scope is not None:
            try:
                scope.dis()
            except Exception:
                pass


def run_board_test(
    category: str,
    seed: int | None,
) -> bool:
    """Run board_test.py for the selected parameter set and random seed."""
    command = [
        sys.executable,
        str(BOARD_TEST),
        category,
    ]

    if seed is not None:
        command.extend(
            [
                "--seed",
                str(seed),
            ]
        )

    result = subprocess.run(
        command,
        cwd=EVALUATION_DIR,
    )

    return result.returncode == 0


def main() -> int:
    """Flash and test the selected firmware variants.
    Record individual results and report the overall test status."""
    parser = argparse.ArgumentParser(
        description=("Flash and validate the unified " "LESS Piñata firmware.")
    )

    parser.add_argument(
        "category",
        nargs="?",
        choices=CATEGORIES,
        help=("test one category; omit to " "test all variants"),
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help=("optional base seed passed " "to board_test.py"),
    )

    args = parser.parse_args()

    categories = (args.category,) if args.category is not None else CATEGORIES

    results = []
    initialize_results_csv()

    print()
    print("=" * 64)
    print(" LESS automated board test")
    print("=" * 64)

    print("Workflow: " "Check HEX -> Flash -> " "Board/reference test")

    for index, category in enumerate(
        categories,
        start=1,
    ):
        print()
        print("#" * 64)

        print(f"# Configuration " f"{index}/{len(categories)}: " f"{category}")

        print("#" * 64)

        category_seed = (
            args.seed
            if args.seed is not None
            else random.SystemRandom().randint(0, 2**32 - 1)
        )

        hex_path = get_hex_path(category)

        if not hex_path.is_file():
            print(f"HEX file missing: " f"{hex_path}")

            log_result(
                category,
                category_seed,
                False,
                False,
                False,
                "HEX file missing",
            )

            results.append(
                (
                    category,
                    False,
                    "HEX file missing",
                )
            )

            continue

        print(f"Flashing: " f"{hex_path.name}")

        if not flash_firmware(hex_path):

            log_result(
                category,
                category_seed,
                True,
                False,
                False,
                "flash failed",
            )

            results.append(
                (
                    category,
                    False,
                    "flash failed",
                )
            )

            continue

        print("Flash: Pass")

        print("Running " "board/reference tests...")

        if not run_board_test(
            category,
            category_seed,
        ):

            log_result(
                category,
                category_seed,
                True,
                True,
                False,
                "board test failed",
            )

            results.append(
                (
                    category,
                    False,
                    "board test failed",
                )
            )

            continue

        log_result(
            category,
            category_seed,
            True,
            True,
            True,
        )

        results.append(
            (
                category,
                True,
                "",
            )
        )

    print()
    print("=" * 64)
    print(" TEST SUMMARY")
    print("=" * 64)

    for category, passed, error in results:
        if passed:
            print(f"Pass  {category}")

        else:
            print(f"Fail  {category}: " f"{error}")

    overall_passed = len(results) == len(categories) and all(
        passed for _, passed, _ in results
    )

    print("=" * 64)

    print("Final result: " + ("Pass" if overall_passed else "Fail"))

    print("=" * 64)

    print(f"CSV summary: {RESULTS_CSV}")

    return 0 if overall_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
