from pathlib import Path
import time
import sys
import chipwhisperer as cw
import subprocess


# Get the directory in which this Python script is located.
here = Path(__file__).resolve().parent

# CROSS PARAMETER SETS
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

# Communication baud rate used by the STM32 programmer.
baudrate = 230400

def release_cdc_acm() -> None:
    """
    Unload the Linux CDC-ACM driver.
    The ChipWhisperer Nano shares its USB device with the Linux
    CDC-ACM serial driver. If this driver is attached to the device,
    ChipWhisperer may not be able to access the USB interfaces directly.
    The driver is therefore unloaded before each connection attempt.
    """
    subprocess.run(["sudo", "modprobe", "-r", "cdc_acm"], check = False)


def flash_firmware(hex_path: Path) -> bool:
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

        # Enter STM32 bootloader mode.
        scope.io.pdic = "high"

        # Reset the target before programming.
        scope.io.nrst = "low"
        time.sleep(0.1)
        scope.io.nrst = "high"
        time.sleep(0.5)

        print(f"Flashing image: {hex_path.name}...")

        cw.program_target(
            scope,
            cw.programmers.STM32FProgrammer,
            str(hex_path),
            baud = baudrate
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

# =============================================================================
# Main
# =============================================================================

def main() -> None:
    """
    If a firmware file is provided as a command-line argument, only that file is flashed.
    Without an argument, all configurations defined in PARAMETER_SETS are flashed sequentially.
    """

    if len(sys.argv) > 1:
        single_file = Path(sys.argv[1])
        success = flash_firmware(single_file)
        sys.exit(0 if success else 1)
    
    # Batch mode
    # If no firmware file was specified, process all CROSS parameter configurations automatically.
    print("Starting automated batch flashing sequence...\n")

    successful_flashes = 0

    for family, category, variant in PARAMETER_SETS:
        # Store the current configuration for readable
        # status and error messages.
        param_key = (family, category, variant)

        # Construct the expected firmware filename.
        # Example:
        #   cross_subroutines_rsdp_1_fast-PINATA.hex
        hex_filename = (f"cross_subroutines_{family.lower()}_{category}_{variant}-PINATA.hex")

        # Build the complete path to the firmware file.
        hex_path = here / hex_filename

        # Print a separator and the configuration currently being processed.
        print("=" * 60)
        print(f" Flashing Configuration: {param_key} ".center(60, "="))
        print("=" * 60)

        # Skip the configuration if the corresponding HEX file does not exist.
        if not hex_path.exists():
            print(f"Binary missing: {hex_filename} -> Skipping configuration.")
            continue

        # Flash the current firmware image.
        success = flash_firmware(hex_path)

        # Stop the batch process if flashing fails.
        # This prevents subsequent configurations from being
        # flashed after a potentially problematic hardware state.
        if not success:
            print(f"Aborting batch execution at {param_key} due to an error.\n")
            break

        successful_flashes += 1

        print("\n" + "-" * 60 + "\n")

    print("\n" + "=" * 60)

    if successful_flashes == len(PARAMETER_SETS):
        print("ALL 18 FIRMWARE CONFIGURATIONS FLASHED SUCCESSFULLY!")
    else:
        print(
            f"FLASHING INCOMPLETE: {successful_flashes}/"
            f"{len(PARAMETER_SETS)} configurations flashed successfully."
        )

    print("=" * 60)

if __name__ == "__main__":
    main()

