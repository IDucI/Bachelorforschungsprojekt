from pathlib import Path
import time
import sys
import chipwhisperer as cw
import subprocess

here = Path(__file__).resolve().parent

PARAMETER_SETS = [
    "toy",
    "cat1_192",
    "cat1_68",
    "cat1_45",
    "cat3_220",
    "cat3_102",
    "cat5_345",
    "cat5_137",
]

baudrate = 230400


def release_cdc_acm() -> None:
    """Release the Linux CDC-ACM driver before connecting to the board."""
    subprocess.run(["sudo", "modprobe", "-r", "cdc_acm"], check=False)


def flash_firmware(hex_path: Path) -> bool:
    """Program the STM32 with the selected firmware HEX file."""
    if not hex_path.exists():
        print(f"Error: Target file '{hex_path.name}' does not exist!")
        return False

    print("Connecting to Scope & Target hardware...")
    scope = None

    try:
        release_cdc_acm()
        time.sleep(2)

        scope = cw.scope()
        scope.default_setup()
        scope.io.clkout = 16e6

        scope.io.pdic = "high"
        scope.io.nrst = "low"
        time.sleep(0.1)
        scope.io.nrst = "high"
        time.sleep(0.5)

        print(f"Flashing image: {hex_path.name}...")

        cw.program_target(
            scope,
            cw.programmers.STM32FProgrammer,
            str(hex_path),
            baud=baudrate,
        )

        print("Firmware flashing completed successfully.")
        return True

    except Exception as err:
        print(f"Flashing process failed: {err}")
        return False

    finally:
        if scope is not None:
            try:
                scope.io.pdic = "low"
                scope.io.nrst = "low"
                time.sleep(0.1)
                scope.io.nrst = "high"
                time.sleep(0.5)
            except Exception as err:
                print(f"Warning: Target reset failed: {err}")

            try:
                scope.dis()
            except Exception as err:
                print(f"Warning: Scope cleanup failed: {err}")


def main() -> None:
    """Flash a selected firmware image or all LESS parameter sets."""
    if len(sys.argv) > 1:
        single_file = Path(sys.argv[1])
        success = flash_firmware(single_file)
        sys.exit(0 if success else 1)

    print("Starting automated batch flashing sequence...\n")

    successful_flashes = 0

    for category in PARAMETER_SETS:
        param_key = category

        hex_filename = f"less_subroutines_{category}-PINATA.hex"
        hex_path = here / hex_filename

        print("=" * 60)
        print(f" Flashing Configuration: {param_key} ".center(60, "="))
        print("=" * 60)

        if not hex_path.exists():
            print(f"Binary missing: {hex_filename} -> Skipping configuration.")
            continue

        success = flash_firmware(hex_path)

        if not success:
            print(f"Aborting batch execution at {param_key} due to an error.\n")
            break

        successful_flashes += 1

        print("\n" + "-" * 60 + "\n")

    print("\n" + "=" * 60)

    if successful_flashes == len(PARAMETER_SETS):
        print("ALL 8 FIRMWARE CONFIGURATIONS FLASHED SUCCESSFULLY!")
    else:
        print(
            f"FLASHING INCOMPLETE: {successful_flashes}/"
            f"{len(PARAMETER_SETS)} configurations flashed successfully."
        )

    print("=" * 60)


if __name__ == "__main__":
    main()
