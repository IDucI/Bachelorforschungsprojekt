import argparse
import csv
import random
import statistics
import sys
from pathlib import Path

import chipwhisperer as cw

# =============================================================================
# Paths and CROSS imports
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
LIBCROSS_DIR = PROJECT_DIR.parent.parent / "libcross"
BUILD_DIR = LIBCROSS_DIR / "build"

if str(LIBCROSS_DIR) not in sys.path:
    sys.path.insert(0, str(LIBCROSS_DIR))

from cross import Cross

from board_test import (
    PARAMETER_SETS,
    baudrate,
    release_cdc_acm,
    random_bytes,
    fz_to_bytes,
    fp_to_bytes,
    output_chunk_size,
    board_run_chunked_subroutine,
    subroutine_convert_restr_vec_to_fp,
    subroutine_restr_vec_by_fp_matrix,
    subroutine_pack_fz_vec,
    subroutine_pack_fz_rsdp_g_vec,
    subroutine_pack_fp_syn,
    subroutine_fz_vec_sub_n,
    subroutine_fp_vec_by_fp_matrix,
    subroutine_fp_vec_by_fp_vec_pointwise,
    subroutine_fz_vec_sub_m,
    subroutine_fz_inf_w_by_fz_matrix,
    subroutine_fp_vec_by_restr_vec_scaled,
    subroutine_fz_dz_norm_n,
    subroutine_fz_dz_norm_m,
    subroutine_fp_dz_norm_synd
)

from run_board_test import get_hex_path, flash_firmware

# =============================================================================
# Settings
# =============================================================================

REPETITIONS = 10
RESULTS_DIR = BASE_DIR / "results"
OUTPUT_FILE = RESULTS_DIR / "runtime_measurement.csv"

# Set to False to keep measurements even when one operation fails.
FAIL_ON_MEASUREMENT_ERROR = False

# =============================================================================
# Reference input generation
# =============================================================================

def create_reference_cases(c, rng):
    """
    Generate test cases using the Python CROSS reference implementation.
    Args:
        c: Initialized CROSS instance for the selected configuration.
        rng: Random number generator used to create reproducible inputs.
    Returns:
        A list of test cases containing subroutine IDs, serialized inputs,
        expected outputs and output lengths.
    """
    # Generate random input material required by the Python reference implementation.
    seed_sk = random_bytes(rng, c.params.keypair_seed_length_bytes)
    message = random_bytes(rng, 32)
    root_seed = random_bytes(rng, c.params.seed_length_bytes)
    salt = random_bytes(rng, c.params.salt_length_bytes)

    # Compute reference values using the Python CROSS implementation.
    keygen = c.calculation.keygen(seed_sk)

    sign = c.calculation.sign(
        message,
        seed_sk = seed_sk,
        pk = keygen.pk,
        root_seed = root_seed,
        salt = salt
    )

    # Select an iteration index for the corresponding test inputs and outputs.
    i = rng.randrange(c.params.t)

    cases = []

    # Store the subroutine name, ID, serialized input and expected output.
    def add(name, subroutine_id, input_data, expected_output):
        cases.append({
            "name": name,
            "id": subroutine_id,
            "input": bytes(input_data),
            "expected_output": bytes(expected_output),
            "output_length": len(expected_output),
        })

    add(
        "convert_restr_vec_to_fp",
        subroutine_convert_restr_vec_to_fp,
        fz_to_bytes(sign.convert_restr_vec_to_fp.v_bar[i]),
        fp_to_bytes(sign.convert_restr_vec_to_fp.v[i], c)
    )

    add(
        "restr_vec_by_fp_matrix",
        subroutine_restr_vec_by_fp_matrix,
        fz_to_bytes(keygen.restr_vec_by_fp_matrix.e_bar)
        + fp_to_bytes(keygen.restr_vec_by_fp_matrix.V_tr, c),
        fp_to_bytes(keygen.restr_vec_by_fp_matrix.s, c)
    )

    add(
        "pack_fp_syn",
        subroutine_pack_fp_syn,
        fp_to_bytes(sign.pack_fp_syn.s_prime_in[i], c),
        bytes(sign.pack_fp_syn.s_prime_out[i])
    )

    add(
        "fz_vec_sub_n",
        subroutine_fz_vec_sub_n,
        fz_to_bytes(sign.fz_vec_sub_n.e_bar)
        + fz_to_bytes(sign.fz_vec_sub_n.e_bar_prime[i]),
        fz_to_bytes(sign.fz_vec_sub_n.v_bar[i])
    )

    add(
        "fp_vec_by_fp_matrix",
        subroutine_fp_vec_by_fp_matrix,
        fp_to_bytes(sign.fp_vec_by_fp_matrix.u[i], c)
        + fp_to_bytes(sign.fp_vec_by_fp_matrix.V_tr, c),
        fp_to_bytes(sign.fp_vec_by_fp_matrix.s_prime[i], c)
    )

    add(
        "fp_vec_by_fp_vec_pointwise",
        subroutine_fp_vec_by_fp_vec_pointwise,
        fp_to_bytes(sign.fp_vec_by_fp_vec_pointwise.u_prime[i], c)
        + fp_to_bytes(sign.fp_vec_by_fp_vec_pointwise.v[i], c),
        fp_to_bytes(sign.fp_vec_by_fp_vec_pointwise.u[i], c)
    )

    add(
        "fp_vec_by_restr_vec_scaled",
        subroutine_fp_vec_by_restr_vec_scaled,
        fz_to_bytes(sign.fp_vec_by_restr_vec_scaled.e_bar_prime[i])
        + fp_to_bytes([sign.fp_vec_by_restr_vec_scaled.chall_1[i]], c)
        + fp_to_bytes(sign.fp_vec_by_restr_vec_scaled.u_prime[i], c),
        fp_to_bytes(sign.fp_vec_by_restr_vec_scaled.y[i], c)
    )

    add(
        "fz_dz_norm_n",
        subroutine_fz_dz_norm_n,
        fz_to_bytes(sign.fz_dz_norm_n.v_bar_in[i]),
        fz_to_bytes(sign.fz_dz_norm_n.v_bar_out[i])
    )

    add(
        "fp_dz_norm_synd",
        subroutine_fp_dz_norm_synd,
        fp_to_bytes(sign.fp_dz_norm_synd.s_prime_in[i], c),
        fp_to_bytes(sign.fp_dz_norm_synd.s_prime_out[i], c)
    )

    # Family-specific subroutines.
    if c.params.algorithm == "RSDP":
        add(
            "pack_fz_vec",
            subroutine_pack_fz_vec,
            fz_to_bytes(sign.pack_fz_vec.v_bar_in[i]),
            bytes(sign.pack_fz_vec.v_bar_out[i])
        )

    elif c.params.algorithm == "RSDPG":
        add(
            "fz_vec_sub_m",
            subroutine_fz_vec_sub_m,
            fz_to_bytes(sign.fz_vec_sub_m.e_G_bar)
            + fz_to_bytes(sign.fz_vec_sub_m.e_G_bar_prime[i]),
            fz_to_bytes(sign.fz_vec_sub_m.v_G_bar[i])
        )

        add(
            "fz_inf_w_by_fz_matrix",
            subroutine_fz_inf_w_by_fz_matrix,
            fz_to_bytes(sign.fz_inf_w_by_fz_matrix.e_G_bar_prime[i])
            + fz_to_bytes(sign.fz_inf_w_by_fz_matrix.W_mat),
            fz_to_bytes(sign.fz_inf_w_by_fz_matrix.e_bar_prime[i])
        )

        add(
            "fz_dz_norm_m",
            subroutine_fz_dz_norm_m,
            fz_to_bytes(sign.fz_dz_norm_m.v_G_bar_in[i]),
            fz_to_bytes(sign.fz_dz_norm_m.v_G_bar_out[i])
        )

        add(
            "pack_fz_rsdp_g_vec",
            subroutine_pack_fz_rsdp_g_vec,
            fz_to_bytes(sign.pack_fz_rsdp_g_vec.v_G_bar_in[i]),
            bytes(sign.pack_fz_rsdp_g_vec.v_G_bar_out[i])
        )

    return cases


# Request the cycle count and CPU clock frequency from the firmware.
def read_cycles(target):
    """
    Retrieve the last measured cycle count and CPU clock frequency.
    Args:
        target: Connected ChipWhisperer SimpleSerial target.
    Returns:
        A tuple containing the cycle count and CPU frequency in Hz.
    Raises:
        TimeoutError: If no response is received.
        RuntimeError: If the cycle count or CPU frequency is invalid.
    """
    target.send_cmd(ord("c"), 0, b"")

    response = target.simpleserial_read("r", 8, timeout = 5000)

    if response is None:
        raise TimeoutError("Timeout while waiting for cycle response")

    # Decode both returned values as little-endian 32-bit integers.
    cycles = int.from_bytes(response[:4], "little")
    cpu_hz = int.from_bytes(response[4:8], "little")

    if cycles <= 0 or cpu_hz <= 0:
        raise RuntimeError(
            f"Invalid cycle count or CPU clock: "
            f"{cycles} cycles, {cpu_hz} Hz"
        )

    return cycles, cpu_hz


# Execute the firmware subroutine and retrieve the complete output in chunks.
def execute_once(target, case):
    """
    Execute one subroutine, retrieve its complete output,
    verify it against the Python reference and read the cycle count.
    """
    actual_output = board_run_chunked_subroutine(
        target=target,
        subroutine_id=case["id"],
        input_data=case["input"],
        output_len=case["output_length"],
        chunk_size=output_chunk_size,
    )

    expected_output = case["expected_output"]

    # Verify correctness by comparing the firmware result with the Python reference.
    if actual_output != expected_output:
        raise AssertionError(
            f"{case['name']}: output differs from Python reference "
            f"(expected {len(expected_output)} bytes, "
            f"received {len(actual_output)} bytes)"
        )
    # Read the cycle count after the result has been retrieved.
    cycles, cpu_hz = read_cycles(target)

    return cycles, cpu_hz

# =============================================================================
# Measurement
# =============================================================================

def connect_board():
    """
    Initialize the ChipWhisperer scope and connect to the target board.
    Returns:
        A tuple containing the initialized scope and SimpleSerial target.
    Raises:
        Exception: If initialization or connection setup fails.
    """
    # Release any existing CDC-ACM connection before opening the scope.
    release_cdc_acm()

    scope = cw.scope()
    target = None

    try:
        # Configure the ChipWhisperer and establish the SimpleSerial connection.
        scope.default_setup()
        scope.io.clkout = 15e6

        target = cw.target(scope, cw.targets.SimpleSerial2)
        target.baud = baudrate
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


# Collect successful cycle measurements, clock frequencies and error messages.
def measure_case(target, case, repetitions):
    """
    Measure a subroutine repeatedly and calculate runtime statistics.
    Failed repetitions are recorded as errors unless configured to abort
    immediately. Successful measurements are summarized using cycle counts
    and execution times.
    Args:
        target: Connected ChipWhisperer SimpleSerial target.
        case: Test case describing the subroutine and expected output.
        repetitions: Number of requested measurement repetitions.
    Returns:
        A dictionary containing repetition counts, runtime statistics,
        CPU frequency and any recorded errors.
    """
    cycles_values = []
    cpu_values = []
    errors = []

    # Repeat the measurement and record each successful execution.
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

            # Reset serial communication before retrying the next sample.
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
        raise RuntimeError(
            f"CPU clock changed during {case['name']}: {cpu_values}"
        )

    cpu_hz = cpu_values[0]
    # Convert cycle counts into execution times using the measured CPU frequency.
    runtime_us = [
        cycles / cpu_hz * 1_000_000
        for cycles in cycles_values
    ]

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
        "stdev_us": (
            statistics.stdev(runtime_us)
            if len(runtime_us) > 1
            else 0.0
        ),
        "error": " | ".join(errors),
    }

# =============================================================================
# CSV output
# =============================================================================

def write_results(rows):
    """
    Write accumulated runtime measurements to a CSV file.
    """
    RESULTS_DIR.mkdir(parents = True, exist_ok = True)

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

    with OUTPUT_FILE.open("w", newline = "", encoding = "utf-8") as file:
        writer = csv.DictWriter(file, fieldnames = fields)
        writer.writeheader()

        for row in rows:
            writer.writerow({
                "family": row["family"],
                "category": row["category"],
                "variant": row["variant"],
                "subroutine": row["subroutine"],
                "repetitions_requested": row["repetitions_requested"],
                "repetitions_completed": row["repetitions_completed"],
                "error": row["error"],
                "cpu_clock_hz": row["cpu_clock_hz"],
                "mean_cycles": row["mean_cycles"],
                "median_cycles": row["median_cycles"],
                "min_cycles": row["min_cycles"],
                "max_cycles": row["max_cycles"],
                "mean_us": (
                    f'{row["mean_us"]:.3f}'
                    if row["mean_us"] != "" else ""
                ),
                "median_us": (
                    f'{row["median_us"]:.3f}'
                    if row["median_us"] != "" else ""
                ),
                "min_us": (
                    f'{row["min_us"]:.3f}'
                    if row["min_us"] != "" else ""
                ),
                "max_us": (
                    f'{row["max_us"]:.3f}'
                    if row["max_us"] != "" else ""
                ),
                "stdev_us": (
                    f'{row["stdev_us"]:.3f}'
                    if row["stdev_us"] != "" else ""
                ),
            })

    print(f"\nCSV results saved to: {OUTPUT_FILE}")

# =============================================================================
# Main
# =============================================================================

def main():
    # Define command-line options for configuration, flashing and repetitions.
    parser = argparse.ArgumentParser(description = "Measure CROSS subroutine runtimes on the ChipWhisperer.")

    parser.add_argument(
        "family",
        nargs = "?",
        choices = ("RSDP", "RSDPG")
    )
    parser.add_argument(
        "category",
        nargs = "?",
        type = int,
        choices = (1, 3, 5)
    )
    parser.add_argument(
        "variant",
        nargs = "?",
        choices = ("fast", "balanced", "small")
    )
    parser.add_argument(
        "--no-flash",
        action = "store_true",
        help="Use the firmware currently flashed on the board."
    )
    parser.add_argument(
        "--seed",
        type = int,
        default = None,
        help = "Seed for selecting reference inputs."
    )
    parser.add_argument(
        "--repetitions",
        type = int,
        default = REPETITIONS,
        help = "Number of runtime measurements per subroutine."
    )

    args = parser.parse_args()

    # Ensure that a manually selected configuration is specified completely.
    supplied = (args.family, args.category, args.variant)

    if any(value is not None for value in supplied) and not all(
        value is not None for value in supplied
    ):
        parser.error("Specify family, category and variant together.")

    if args.no_flash and not all(value is not None for value in supplied):
        parser.error("--no-flash requires one explicit configuration.")

    if args.repetitions < 1:
        parser.error("--repetitions must be at least 1.")

    # Use one explicitly selected configuration or process all parameter sets.
    if all(value is not None for value in supplied):
        configurations = [supplied]
    else:
        configurations = PARAMETER_SETS

    # Generate a random seed if none was provided, allowing reproducible test cases.
    seed = (
        args.seed
        if args.seed is not None
        else random.SystemRandom().randint(0, 2**32 - 1)
    )

    print("=" * 70)
    print("CROSS Runtime Measurement")
    print("=" * 70)
    print(f"Configurations: {len(configurations)}")
    print(f"Repetitions per subroutine: {args.repetitions}")
    print(f"Random seed: {seed}")
    print(f"Flash firmware: {not args.no_flash}")

    rows = []
    overall_failed = False

    for index, (family, category, variant) in enumerate(
        configurations, start=1
    ):
        print("\n" + "=" * 70)
        print(
            f"Configuration {index}/{len(configurations)}: "
            f"{family} Cat-{category} {variant}"
        )
        print("=" * 70)

        # Flash the matching firmware unless the existing firmware should be used.
        if not args.no_flash:
            hex_path = get_hex_path(family, category, variant)

            if not hex_path.is_file():
                print(f"ERROR: Firmware not found: {hex_path}")
                overall_failed = True
                continue

            if not flash_firmware(hex_path):
                print(f"ERROR: Firmware flashing failed: {hex_path}")
                overall_failed = True
                continue

        # Initialize the Python reference implementation for this configuration.
        c = Cross(
            path = str(BUILD_DIR),
            algorithm = family,
            category = category,
            optimization = variant
        )

        # Derive a configuration-specific seed to reproduce the generated test data.
        config_seed = (
            seed
            + category * 100000
            + (1000000 if family == "RSDPG" else 0)
            + {"fast": 1, "balanced": 2, "small": 3}[variant]
        )
        rng = random.Random(config_seed)

        # Generate inputs and expected outputs for all applicable subroutines.
        cases = create_reference_cases(c, rng)

        # Connect to the target board before starting the measurements.
        scope, target = connect_board()

        try:
            for case in cases:
                print(
                    f"\n  {case['name']} "
                    f"(ID 0x{case['id']:02X}, "
                    f"input={len(case['input'])} bytes, "
                    f"output={case['output_length']} bytes)"
                )

                measurement = measure_case(
                    target,
                    case,
                    args.repetitions
                )

                if measurement["repetitions_completed"] == 0:
                    overall_failed = True

                rows.append({
                    "family": family,
                    "category": category,
                    "variant": variant,
                    "subroutine": case["name"],
                    **measurement,
                })

        finally:
            try:
                target.dis()
            finally:
                scope.dis()

        # Persist results after each configuration so partial results survive
        # a later failure.
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
