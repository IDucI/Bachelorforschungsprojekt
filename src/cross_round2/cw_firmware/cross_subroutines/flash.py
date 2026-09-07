import logging
import time
from pathlib import Path
import chipwhisperer as cw

# =============================================================================
# LOGGING SETUP
# =============================================================================

logging.getLogger("chipwhisperer").setLevel(logging.ERROR)

HERE = Path(__file__).resolve().parent

# =============================================================================
# CROSS PARAMETER SETS (family, category, variant)
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

BAUDRATE = 230400


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main() -> None:
    print("Connecting to ChipWhisperer Scope...")
    scope = cw.scope()
    scope.default_setup()
    scope.io.clkout = 15e6
    print("clkout:", scope.io.clkout)
    time.sleep(0.5)

    try:
        for family, category, variant in PARAMETER_SETS:
            param_key = (family, category, variant)
            hex_filename = f"cross_subroutines_{family.lower()}_{category}_{variant}-PINATA.hex"
            hex_path = HERE / hex_filename

            if not hex_path.exists():
                print(f"\nFirmware not found: {hex_filename} - skipping {param_key}")
                continue

            print("\n" + "=" * 60)
            print(f" Flashing and verifying set: {param_key} ".center(60, "="))
            print("=" * 60)

            # Flashing
            print(f"[*] Flashing target with: {hex_filename}...")
            cw.program_target(
                scope,
                cw.programmers.STM32FProgrammer,
                str(hex_path),
                baud=BAUDRATE,
            )
            print("Flashing successful!")

            # SimpleSerial Target connection setup
            target = cw.target(scope, cw.targets.SimpleSerial2)
            target.baud = BAUDRATE
            target.flush()

            # Quick communication verification
            test_payload = bytes([1, 2, 3])
            target.send_cmd("s", 0x80, test_payload)
            resp = target.simpleserial_read("r", 3)

            print("Readback:", resp)

            if resp is not None and list(resp) == list(test_payload):
                print("OK: SimpleSerial responsiveness verified.")
            else:
                print("ERROR: Unexpected readback response.")

            # Disconnect target interface to free the port for the next firmware iteration
            target.dis()

        print("\n" + "=" * 60)
        print(" All available firmware sets successfully flashed and verified ".center(60, "="))
        print("=" * 60 + "\n")

    except Exception as err:
        print(f"\n[-] Critical error: {err}")

    finally:
        scope.dis()
        print("Scope safely disconnected.")


if __name__ == "__main__":
    main()