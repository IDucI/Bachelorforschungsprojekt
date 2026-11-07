import csv
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS_CSV = HERE / "cachegrind_results.csv"

RUNTIME_REPETITIONS = 5

OVERALL_BENCHMARKS = {
    "CROSS_keygen",
    "CROSS_sign",
    "CROSS_verify",
}

METRICS = [
    "I refs",
    "I1 misses",
    "LLi misses",
    "D refs",
    "D1 misses",
    "LLd misses",
    "Branches",
    "Mispredicts",
]

def run_runtime(target):
    """
    Measure the host-side runtime of one benchmark executable.
    The benchmark is executed multiple times and the average runtime is returned.
    """
    times = []

    print(f"Measuring runtime of {target} ({RUNTIME_REPETITIONS} runs)...")

    for _ in range(RUNTIME_REPETITIONS):
        command = [
            "/usr/bin/time",
            "-f",
            "%e",
            f"./{target}",
        ]

        result = subprocess.run(
            command,
            cwd = HERE,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
            text = True,
            check = True
        )

        # /usr/bin/time writes the measured time to stderr.
        match = re.search(r"^\d+\.\d+$", result.stderr.strip(), re.MULTILINE)

        if not match:
            raise RuntimeError(
                f"Could not determine runtime for {target}.\n"
                f"time output:\n{result.stderr}"
            )

        times.append(float(match.group(0)))

    average = sum(times) / len(times)

    print(f"  Runtime: {average:.5f} s")

    return average

def parse_number(value):
    """
    Convert Cachegrind numbers such as 36,460,976 to int.
    """
    return int(value.replace(",", ""))


def parse_cachegrind_output(output):
    """
    Extract the relevant Cachegrind statistics from Valgrind output.
    """
    values = {}

    patterns = {
        "I refs": r"I refs:\s*([\d,]+)",
        "I1 misses": r"I1\s+misses:\s*([\d,]+)",
        "LLi misses": r"LLi misses:\s*([\d,]+)",
        "D refs": r"D refs:\s*([\d,]+)",
        "D1 misses": r"D1\s+misses:\s*([\d,]+)",
        "LLd misses": r"LLd misses:\s*([\d,]+)",
        "Branches": r"Branches:\s*([\d,]+)",
        "Mispredicts": r"Mispredicts:\s*([\d,]+)",
    }

    for metric, pattern in patterns.items():
        match = re.search(pattern, output)

        if match:
            values[metric] = parse_number(match.group(1))

    missing = [metric for metric in METRICS if metric not in values]

    if missing:
        raise RuntimeError("Could not find the following Cachegrind metrics: " + ", ".join(missing))

    return values


def run_cachegrind(target):
    """
    Run one benchmark executable through Cachegrind.
    """
    command = [
        "valgrind",
        "--tool=cachegrind",
        "--cache-sim=yes",
        "--branch-sim=yes",
        f"./{target}",
    ]

    print()
    print("-" * 60)
    print(f"Running {target}")
    print("-" * 60)

    result = subprocess.run(
        command,
        cwd = HERE,
        stdout = subprocess.PIPE,
        stderr = subprocess.STDOUT,
        text = True,
        check = True
    )
    return parse_cachegrind_output(result.stdout)


def target_to_names(target):
    """
    F.e, Convert: cachegrind_convert_restr_vec_to_fp_rsdp_1_fast
    into: benchmark = convert_restr_vec_to_fp variant = rsdp_1_fast
    """
    prefix = "cachegrind_"

    if not target.startswith(prefix):
        raise ValueError(f"Unexpected target name: {target}")

    name = target[len(prefix):]

    variants = [
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

    for variant in variants:
        suffix = "_" + variant

        if name.endswith(suffix):
            benchmark = name[:-len(suffix)]
            return benchmark, variant

    raise ValueError(f"Could not determine variant from target: {target}")


def write_csv(rows):
    """
    Write all measurements to the CSV file.
    """
    fieldnames = [
        "Benchmark",
        "Variant",
        "I_refs",
        "I1_misses",
        "LLi_misses",
        "D_refs",
        "D1_misses",
        "LLd_misses",
        "Branches",
        "Mispredicts",
        "Runtime_s",
        "Seconds_per_instruction",
    ]

    with RESULTS_CSV.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print()
    print("=" * 60)
    print(f"CSV written to:")
    print(RESULTS_CSV)
    print(f"Measurements: {len(rows)}")
    print("=" * 60)


def main():
    import sys

    overall_benchmarks = [
        "CROSS_keygen",
        "CROSS_sign",
        "CROSS_verify",
    ]

    common_benchmarks = [
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

    rsdpg_benchmarks = [
        "fz_inf_w_by_fz_matrix",
        "fz_vec_sub_m",
        "fz_dz_norm_m",
    ]

    variants = [
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

    rsdpg_variants = [
        variant
        for variant in variants
        if variant.startswith("rsdpg_")
    ]

    # ------------------------------------------------------------------------
    # Determine requested mode
    # ------------------------------------------------------------------------
    if len(sys.argv) != 2:
        print("Usage:")
        print("  python3 collect_cachegrind.py <benchmark>")
        print("  python3 collect_cachegrind.py all")
        print()
        print("Available benchmarks:")

        for benchmark in overall_benchmarks:
            print(f"  {benchmark}")

        for benchmark in common_benchmarks:
            print(f"  {benchmark}")

        for benchmark in rsdpg_benchmarks:
            print(f"  {benchmark}")

        return 1

    requested = sys.argv[1]

    if requested == "all":
        benchmarks = (overall_benchmarks + common_benchmarks + rsdpg_benchmarks)

        # Overall + common use all 18 variants.
        # RSDPG-specific benchmarks are handled separately below.
        benchmark_groups = [
            (overall_benchmarks, variants),
            (common_benchmarks, variants),
            (rsdpg_benchmarks, rsdpg_variants),
        ]

    # Individual overall benchmark
    elif requested in overall_benchmarks:
        benchmark_groups = [([requested], variants)]

    # Individual common benchmark
    elif requested in common_benchmarks:
        benchmark_groups = [([requested], variants)]

    # Individual RSDPG benchmark
    elif requested in rsdpg_benchmarks:
        benchmark_groups = [([requested], rsdpg_variants)]

    else:
        print(f"Unknown benchmark: {requested}")
        print()
        print("Available benchmarks:")

        for benchmark in overall_benchmarks:
            print(f"  {benchmark}")

        for benchmark in common_benchmarks:
            print(f"  {benchmark}")

        for benchmark in rsdpg_benchmarks:
            print(f"  {benchmark}")

        print("  all")

        return 1

    rows = []

    for benchmarks, selected_variants in benchmark_groups:

        for benchmark in benchmarks:

            for variant in selected_variants:

                target = f"cachegrind_{benchmark}_{variant}"

                metrics = run_cachegrind(target)

                runtime = run_runtime(target)
                seconds_per_instruction = runtime / metrics["I refs"]

                rows.append({
                    "Benchmark": benchmark,
                    "Variant": variant,
                    "I_refs": metrics["I refs"],
                    "I1_misses": metrics["I1 misses"],
                    "LLi_misses": metrics["LLi misses"],
                    "D_refs": metrics["D refs"],
                    "D1_misses": metrics["D1 misses"],
                    "LLd_misses": metrics["LLd misses"],
                    "Branches": metrics["Branches"],
                    "Mispredicts": metrics["Mispredicts"],
                    "Runtime_s": runtime,
                    "Seconds_per_instruction": seconds_per_instruction,
                })

    write_csv(rows)

    return 0

if __name__ == "__main__":
    main()