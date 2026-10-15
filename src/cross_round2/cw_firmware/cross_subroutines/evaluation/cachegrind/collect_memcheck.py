import csv
import re
import subprocess
import sys
from pathlib import Path

# Path setup
evaluation_dir = Path(__file__).resolve().parent
results_csv = evaluation_dir / "memcheck_results.csv"

# CROSS variants
VARIANTS = [
    "rsdp_1_fast",
    "rsdp_1_balanced",
    "rsdp_1_small",
    "rsdp_3_fast",
    "rsdp_3_balanced",
    "rsdp_3_small",
    "rsdp_5_fast",
    "rsdp_5_balanced",
    "rsdp_5_small",
    "rsdpg_1_fast",
    "rsdpg_1_balanced",
    "rsdpg_1_small",
    "rsdpg_3_fast",
    "rsdpg_3_balanced",
    "rsdpg_3_small",
    "rsdpg_5_fast",
    "rsdpg_5_balanced",
    "rsdpg_5_small",
]

RSDPG_VARIANTS = [
    "rsdpg_1_fast",
    "rsdpg_1_balanced",
    "rsdpg_1_small",
    "rsdpg_3_fast",
    "rsdpg_3_balanced",
    "rsdpg_3_small",
    "rsdpg_5_fast",
    "rsdpg_5_balanced",
    "rsdpg_5_small",
]

OVERALL_BENCHMARKS = [
    "CROSS_keygen",
    "CROSS_sign",
    "CROSS_verify",
]

COMMON_BENCHMARKS = [
    "convert_restr_vec_to_fp",
    "restr_vec_by_fp_matrix",
    "fp_vec_by_fp_vec_pointwise",
    "fp_vec_by_fp_matrix",
    "fz_vec_sub_n",
    "expand_sk",
    "fz_dz_norm_n",
    "fp_vec_by_restr_vec_scaled",
    "expand_digest_to_fixed_weight",
    "pack_fp_syn",
    "pack_fz_vec",
    "expand_pk",
]

RSDPG_BENCHMARKS = [
    "fz_inf_w_by_fz_matrix",
    "fz_vec_sub_m",
    "fz_dz_norm_m",
]

# Valgrind
VALGRIND_OPTIONS = [
    "valgrind",
    "--tool=memcheck",
    "--leak-check=full",
    "--show-leak-kinds=all",
]

# =============================================================================
# Parsing
# =============================================================================

def parse_number(value):
    """Convert Valgrind numbers such as '1,024' to integers."""
    return int(value.replace(",", ""))


def parse_memcheck_output(output):
    """
    Extract heap and error information from Valgrind Memcheck output.
    """
    result = {
        "Allocs": None,
        "Frees": None,
        "Bytes_Allocated": None,
        "Bytes_In_Use": None,
        "Blocks_In_Use": None,
        "Errors": None
    }

    # Example:
    # total heap usage: 1 allocs, 1 frees, 1,024 bytes allocated
    heap_match = re.search(
        r"total heap usage:\s*"
        r"([\d,]+)\s+allocs,\s*"
        r"([\d,]+)\s+frees,\s*"
        r"([\d,]+)\s+bytes allocated",
        output
    )

    if heap_match:
        result["Allocs"] = parse_number(heap_match.group(1))
        result["Frees"] = parse_number(heap_match.group(2))
        result["Bytes_Allocated"] = parse_number(heap_match.group(3))

    # Example:
    # in use at exit: 0 bytes in 0 blocks
    exit_match = re.search(
        r"in use at exit:\s*"
        r"([\d,]+)\s+bytes in\s+([\d,]+)\s+blocks",
        output
    )

    if exit_match:
        result["Bytes_In_Use"] = parse_number(exit_match.group(1))
        result["Blocks_In_Use"] = parse_number(exit_match.group(2))

    # Example:
    # ERROR SUMMARY: 0 errors from 0 contexts
    error_match = re.search(r"ERROR SUMMARY:\s*([\d,]+)\s+errors", output)

    if error_match:
        result["Errors"] = parse_number(error_match.group(1))

    return result

# =============================================================================
# Run one benchmark
# =============================================================================

def run_memcheck(benchmark, variant):
    binary = (evaluation_dir / f"cachegrind_{benchmark}_{variant}")

    if not binary.exists():
        print(f"ERROR: Binary not found: {binary}")
        return None

    print()
    print("=" * 70)
    print(f"Benchmark: {benchmark}")
    print(f"Variant:   {variant}")
    print("=" * 70)

    command = VALGRIND_OPTIONS + [str(binary)]

    process = subprocess.run(
        command,
        stdout = subprocess.PIPE,
        stderr = subprocess.STDOUT,
        text = True
    )
    output = process.stdout

    print(output)

    if process.returncode != 0:
        print(
            f"ERROR: Memcheck failed for {binary} "
            f"(exit code {process.returncode})"
        )
        return None

    result = parse_memcheck_output(output)

    result["Benchmark"] = benchmark
    result["Variant"] = variant

    return result

# =============================================================================
# CSV
# =============================================================================

def write_csv(results):
    fieldnames = [
        "Benchmark",
        "Variant",
        "Allocs",
        "Frees",
        "Bytes_Allocated",
        "Bytes_In_Use",
        "Blocks_In_Use",
        "Errors",
    ]

    with open(results_csv, "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        writer.writeheader()

        for result in results:
            writer.writerow(result)

# =============================================================================
# Benchmark selection
# =============================================================================

def get_benchmarks(argument):
    if argument == "all":
        return (OVERALL_BENCHMARKS + COMMON_BENCHMARKS + RSDPG_BENCHMARKS)

    all_benchmarks = (OVERALL_BENCHMARKS + COMMON_BENCHMARKS + RSDPG_BENCHMARKS)

    if argument in all_benchmarks:
        return [argument]

    raise ValueError(f"Unknown benchmark: {argument}")


def get_variants(benchmark):
    if benchmark in RSDPG_BENCHMARKS:
        return RSDPG_VARIANTS

    return VARIANTS


def main():
    if len(sys.argv) != 2:
        print()
        print("Usage:")
        print("  python3 collect_memcheck.py <benchmark>")
        print()
        print("Examples:")
        print("  python3 collect_memcheck.py convert_restr_vec_to_fp")
        print("  python3 collect_memcheck.py fz_inf_w_by_fz_matrix")
        print("  python3 collect_memcheck.py all")
        print()

        sys.exit(1)

    argument = sys.argv[1]

    benchmarks = get_benchmarks(argument)

    results = []

    for benchmark in benchmarks:
        variants = get_variants(benchmark)

        for variant in variants:
            result = run_memcheck(benchmark, variant)

            if result is not None:
                results.append(result)

    write_csv(results)

    print()
    print("=" * 70)
    print("Memcheck evaluation finished")
    print("=" * 70)
    print(f"Results written to:")
    print(results_csv)
    print(f"Measurements: {len(results)}")


if __name__ == "__main__":
    main()