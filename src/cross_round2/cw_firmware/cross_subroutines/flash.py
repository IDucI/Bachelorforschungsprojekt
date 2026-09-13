import logging
import time
from pathlib import Path
import chipwhisperer as cw
import sys

# =============================================================================
# PATH SETUP & IMPORTS
# =============================================================================

# Determine directory of the current script (.../cw_firmware/cross_subroutines)
HERE = Path(__file__).resolve().parent

# Calculate path to libcross: two levels up to project root, then into "libcross"
LIBCROSS_DIR = HERE.parent.parent / "libcross"
BUILD_DIR = LIBCROSS_DIR / "build"  


# MUST append to sys.path BEFORE importing modules from libcross
if str(LIBCROSS_DIR) not in sys.path:
    sys.path.insert(0, str(LIBCROSS_DIR))

# Define directory containing the test vector JSON files
TESTS_DIR = LIBCROSS_DIR

# Import ChipWhisperer and local libcross modules
import chipwhisperer as cw
from cross import Cross, Calculations

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

def run_tests_for_variant(target, family: str, category: int, variant: str) -> bool:
    """
    Run functional and reference test vectors directly on the connected target.
    """
    print(f"Starting tests for {family} Cat-{category} ({variant})...")
    
    # Initialize Cross instance with the active serial target
    c = Cross(
        path=str(BUILD_DIR),
        algorithm=family,
        category=category,
        optimization=variant,
        release="_6.6.87.so"
    )

    # Assign Target to the subfunctions object (or directly to c)
    if hasattr(c, "subfunctions"):
        c.subfunctions.target = target
    else:
        c.target = target

    # Keygen -> Sign -> Verify workflow
    print("  -> Testing Keygen, Sign & Verify...")
    sk, pk = c.keygen()
    message = list(b"Hello CROSS")
    signature = c.sign(sk, message)
    is_valid = c.verify(pk, message, signature)

    if not is_valid:
        print("Error: Signature verification failed.")
        return False
    print("Signature verification successful.")

    # Validate intermediate calculations against static JSON test vectors
    json_path = TESTS_DIR / f"cross_{family.lower()}_{category}_{variant}.json"
    if json_path.exists():
        import json
        print(f"  -> Validating vectors against {json_path.name}...")
        with open(json_path, "r") as f:
            data = json.load(f)

        calc = Calculations(c.subfunctions)
        seed_sk = bytes.fromhex(data["seed_sk"])
        root_seed = bytes.fromhex(data["root_seed"])
        salt = bytes.fromhex(data["salt"])

        # Compute v_bar_pre_norm on board hardware
        v_bar_pre_norm = calc.v_bar_pre_norm(seed_sk, root_seed, salt)
        v_bar_pre_norm_ref = data["v_bar_pre_norm"]

        if v_bar_pre_norm == v_bar_pre_norm_ref:
            print("Vector-Match (v_bar_pre_norm): MATCH")
        else:
            print("Error: Vector-Match (v_bar_pre_norm): MISMATCH")
            return False
    else:
        print(f"Warning: No JSON test vector file found at {json_path}")

    return True

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
            print(f" Flashing and testing set: {param_key} ".center(60, "="))
            print("=" * 60)

            # Flash target firmware
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

            # Execute test workflow for current firmware iteration
            success = run_tests_for_variant(target, family, category, variant)

            if success:
                print(f"\n[PASS] {param_key} fully functional")
            else:
                print(f"\n[FAIL] {param_key} didn't pass the test")

            # Disconnect target interface to prepare for next flash cycle
            target.dis()
            
    except Exception as err:
        print(f"\n[-] Critical error: {err}")

    finally:
        scope.dis()
        print("Scope safely disconnected.")


if __name__ == "__main__":
    main()