import argparse
import subprocess
import sys
from pathlib import Path
import random

EVALUATION_DIR = Path(__file__).resolve().parent
FIRMWARE_DIR = EVALUATION_DIR.parent
BOARD_TEST = EVALUATION_DIR / "board_test.py"

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


def get_hex_path(
    category: str,
) -> Path:
    """Return the expected firmware HEX path for a parameter set."""
    return FIRMWARE_DIR / (f"less_subroutines_" f"{category}-PINATA.hex")


def flash_firmware(
    hex_path: Path,
) -> bool:
    """Flash the selected firmware using flash.py."""
    result = subprocess.run(
        [sys.executable, str(FIRMWARE_DIR / "flash.py"), str(hex_path)],
        cwd=FIRMWARE_DIR,
        check=False,
    )

    return result.returncode == 0


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

            results.append(
                (
                    category,
                    False,
                    "board test failed",
                )
            )

            continue

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

    return 0 if overall_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
