import subprocess
import sys
import csv
from datetime import datetime
from pathlib import Path

# =============================================================================
# Path setup
# =============================================================================

evaluation_dir = Path(__file__).resolve().parent
project_dir = evaluation_dir.parent

board_test_script = evaluation_dir / "board_test.py"
flash_script = project_dir / "flash.py"

results_csv = evaluation_dir / "board_test_results.csv"

# =============================================================================
# Parameter Set
# =============================================================================

PARAMETER_SETS = [
    ("RSDP", 1, "fast"),
    ("RSDP", 1, "balanced"),
    ("RSDP", 1, "small"),
    ("RSDP", 3, "fast"),
    ("RSDP", 3, "balanced"),
    ("RSDP", 3, "small"),
    ("RSDP", 5, "fast"),
    ("RSDP", 5, "balanced"),
    ("RSDP", 5, "small"),
    ("RSDPG", 1, "fast"),
    ("RSDPG", 1, "balanced"),
    ("RSDPG", 1, "small"),
    ("RSDPG", 3, "fast"),
    ("RSDPG", 3, "balanced"),
    ("RSDPG", 3, "small"),
    ("RSDPG", 5, "fast"),
    ("RSDPG", 5, "balanced"),
    ("RSDPG", 5, "small"),
]

# =============================================================================
# CSV Logic
# =============================================================================

def initialize_results_csv() -> None:
    with results_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        writer.writerow(
            [
                "timestamp",
                "family",
                "category",
                "variant",
                "hex_exists",
                "board_test_passed",
                "error"
            ]
        )

def log_result(
    family: str,
    category: int,
    variant: str,
    hex_exists: bool,
    board_test_passed: bool,
    error: str
) -> None:

    with results_csv.open("a", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                family,
                category,
                variant,
                hex_exists,
                board_test_passed,
                error
            ]
        )

# =============================================================================
# Firmware name
# =============================================================================

def get_hex_path(family: str, category: int, variant: str) -> Path:

    filename = (f"cross_subroutines_{family.lower()}_{category}_{variant}-PINATA.hex")

    return project_dir / filename

# =============================================================================
# Flash firmware
# =============================================================================

def flash_firmware(hex_path: Path) -> bool:
    print()
    print("=" * 70)
    print(" Flash firmware")
    print("=" * 70)
    print(f"HEX: {hex_path.name}")

    result = subprocess.run(
        [
            sys.executable,
            str(flash_script),
            str(hex_path),
        ],
        cwd = project_dir,
    )

    if result.returncode != 0:
        print("Firmware flashing failed.")
        return False

    return True

# =============================================================================
# Board test
# =============================================================================

def run_board_test(family: str, category: int, variant: str) -> bool:
    print()
    print("=" * 70)
    print(" Board reference test")
    print("=" * 70)

    print(f"Testing: {family} Cat-{category} {variant}")

    result = subprocess.run(
        [
            sys.executable,
            str(board_test_script),
            family,
            str(category),
            variant,
        ],
        cwd = evaluation_dir
    )

    if result.returncode != 0:

        print("Board reference test failed.")

        return False

    print("Board reference test passed.")

    return True

# =============================================================================
# Main
# =============================================================================

def main() -> int:

    if len(sys.argv) == 1:
        # No arguments -> test all configurations.
        configurations = PARAMETER_SETS
    elif len(sys.argv) == 4:
        # Arguments:
        #   python3 run_board_tests.py FAMILY CATEGORY VARIANT
        family = sys.argv[1]
        category = int(sys.argv[2])
        variant = sys.argv[3]

        configurations = [
            (family, category, variant)
        ]
    else:
        print()
        print("Usage:")
        print("  python3 run_board_tests.py")
        print("  python3 run_board_tests.py FAMILY CATEGORY VARIANT")
        print()
        print("Examples:")
        print("  python3 run_board_tests.py")
        print("  python3 run_board_tests.py RSDP 1 fast")
        print("  python3 run_board_tests.py RSDPG 5 small")

        return 1

    print()
    print("=" * 70)
    print(" CROSS automated board test")
    print("=" * 70)

    print()
    print(f"Configurations: {len(configurations)}")

    print("Workflow:")

    print("    Check HEX -> Flash Firmware -> Board Reference Test")

    initialize_results_csv()

    results = []

    for index, (family, category, variant) in enumerate(configurations, start=1):
        print()
        print()
        print("#" * 70)

        print(f"# Configuration {index}/{len(configurations)}")

        print(f"# {family} Cat-{category} {variant}")

        print("#" * 70)

        hex_path = get_hex_path(family, category, variant)

        # Check HEX
        if not hex_path.exists():
            print()
            print("HEX file not found:")

            print(f"    {hex_path}")

            log_result(
                family,
                category,
                variant,
                hex_exists = False,
                board_test_passed = False,
                error = "HEX file missing"
            )

            results.append(
                (
                    family,
                    category,
                    variant,
                    False,  
                    False,  
                    False,  
                    "HEX file missing"
                )
            )

            # Continue with the next configuration.
            continue

        # Flash firmware
        flash_ok = flash_firmware(hex_path)

        if not flash_ok:
            log_result(
                family,
                category,
                variant,
                hex_exists = True,
                board_test_passed = False,
                error = "Firmware flashing failed"
            )

            results.append(
                (
                    family,
                    category,
                    variant,
                    True,
                    False,
                    False,
                    "Firmware flashing failed"
                )
            )

            continue

        # Board test
        board_ok = run_board_test(family, category, variant)

        if board_ok:
            error = ""
        else:
            error = "Board reference test failed"

        log_result(
            family,
            category,
            variant,
            hex_exists = True,
            board_test_passed = board_ok,
            error = error
        )

        results.append(
            (
                family,
                category,
                variant,
                True,
                True,
                board_ok,
                error
            )
        )

    print()
    print()
    print("=" * 70)
    print(" TEST SUMMARY")
    print("=" * 70)

    for (
        family,
        category,
        variant,
        hex_exists,
        flash_passed,
        board_test_passed,
        error
    ) in results:

        passed = (
            hex_exists
            and flash_passed
            and board_test_passed
        )

        status = "Pass" if passed else "Fail"

        print(
            f"{status:>5}  "
            f"{family:<5} "
            f"Cat-{category:<1} "
            f"{variant:<8}"
            + (
                f"  ({error})"
                if error
                else ""
            )
        )

    # Final result
    all_passed = (
        len(results) == len(configurations)
        and all(
            result[3] and result[4] and result[5]
            for result in results
        )
    )

    print()
    print("=" * 70)

    if all_passed:
        print("Final result: pass")

        print("=" * 70)

        return 0

    print("Final result: Fail")

    print("=" * 70)

    return 1

if __name__ == "__main__":
    sys.exit(main())