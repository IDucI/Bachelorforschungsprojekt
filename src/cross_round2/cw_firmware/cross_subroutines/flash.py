from pathlib import Path
import time
import sys
import chipwhisperer as cw
import subprocess


# =============================================================================
# Path setup
# =============================================================================

# Get the directory in which this Python script is located.
# This ensures that the firmware files can be found independently
# of the directory from which the script is executed.
here = Path(__file__).resolve().parent

# =============================================================================
# CROSS PARAMETER SETS
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


# Communication baud rate used by the STM32 programmer.
baudrate = 230400

# =============================================================================
# USB / CDC-ACM driver handling
# =============================================================================

def release_cdc_acm() -> None:
    """
    Unload the Linux CDC-ACM driver.
    The ChipWhisperer Nano shares its USB device with the Linux
    CDC-ACM serial driver. If this driver is attached to the device,
    ChipWhisperer may not be able to access the USB interfaces directly.
    The driver is therefore unloaded before each connection attempt.
    """
    subprocess.run(["sudo", "modprobe", "-r", "cdc_acm"], check=False)

# =============================================================================
# Firmware flashing
# =============================================================================

def flash_firmware(hex_path: Path) -> bool:
    """
    Flash one firmware image onto the STM32F target.
    """
    # Check whether the specified firmware file exists.
    if not hex_path.exists():
        print(f"Error: Target file '{hex_path.name}' does not exist!")
        return False

    print(" Connecting to Scope & Target hardware...")

    # Scope object is initialized as None so that it can safely
    # be checked in the finally block.
    scope = None

    try:
        # Release the CDC-ACM driver before accessing the
        # ChipWhisperer USB device.
        release_cdc_acm()

        # Establish a connection to the ChipWhisperer scope.
        scope = cw.scope()

        # Apply ChipWhisperer's default scope configuration.
        scope.default_setup()

        # Configure the output clock used by the target.
        scope.io.clkout = 15e6

        # Give the target a short amount of time to stabilize
        # after the clock configuration.
        time.sleep(0.2)

        print(f"Flashing image: {hex_path.name}...")

        # Program the STM32F target with the selected firmware.
        # STM32F Programmer is used for the STM32F4 target on the Riscure Piñata board.
        cw.program_target(scope, cw.programmers.STM32FProgrammer, str(hex_path), baud = baudrate)

        print("Firmware flashing completed successfully.")
        return True

    except Exception as err:
        # Catch any error during USB communication, scope
        # initialization or firmware flashing.
        print(f"Flashing process failed: {err}")
        return False

    finally:
        # Always disconnect the ChipWhisperer scope after the
        # flashing attempt if a connection was successfully created.
        if scope is not None:
            scope.dis()
            print("Scope disconnected.")

# =============================================================================
# Main
# =============================================================================

def main() -> None:
    """
    If a firmware file is provided as a command-line argument, only that file is flashed.
    Without an argument, all configurations defined in PARAMETER_SETS are flashed sequentially.
    """

    # Single-file mode
    # Example: python3 flash.py firmware.hex
    # In this mode, only the specified firmware image is flashed.
    if len(sys.argv) > 1:
        single_file = Path(sys.argv[1])
        flash_firmware(single_file)
        return
    
    # Batch mode
    # If no firmware file was specified, automatically process, all CROSS parameter configurations.
    print("Starting automated batch flashing sequence...\n")

    for family, category, variant in PARAMETER_SETS:
        # Store the current configuration for readable
        # status and error messages.
        param_key = (family, category, variant)

        # Construct the expected firmware filename.
        #
        # Example:
        #   cross_subroutines_rsdp_1_fast-PINATA.hex
        hex_filename = (f"cross_subroutines_{family.lower()}_{category}_{variant}-PINATA.hex")

        # Build the complete path to the firmware file.
        hex_path = here / hex_filename

        # Print a separator and the configuration currently
        # being processed.
        print("=" * 60)
        print(f" Flashing Configuration: {param_key} ".center(60, "="))
        print("=" * 60)

        # Skip the configuration if the corresponding HEX file
        # does not exist.
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

        print("\n" + "-" * 60 + "\n")

if __name__ == "__main__":
    main()

