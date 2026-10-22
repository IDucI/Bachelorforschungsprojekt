import argparse
import csv
import re
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
VARIANTS = (
    "toy",
    "cat1_192",
    "cat1_68",
    "cat1_45",
    "cat3_220",
    "cat3_102",
    "cat5_345",
    "cat5_137",
)
SUBROUTINES = (
    "fq_inv",
    "row_mul3",
    "generator_sample",
    "monomial_sample_prikey",
    "generator_monomial_mul",
)
METRICS = {
    "I_refs": r"I\s+refs:\s*([\d,]+)",
    "I1_misses": r"I1\s+misses:\s*([\d,]+)",
    "LLi_misses": r"LLi misses:\s*([\d,]+)",
    "D_refs": r"D\s+refs:\s*([\d,]+)",
    "D1_misses": r"D1\s+misses:\s*([\d,]+)",
    "LLd_misses": r"LLd misses:\s*([\d,]+)",
    "Branches": r"Branches:\s*([\d,]+)",
    "Mispredicts": r"Mispredicts:\s*([\d,]+)",
}


def benchmarks_for(selection):
    if selection in ("all", "subroutines"):
        return SUBROUTINES
    if selection not in SUBROUTINES:
        raise ValueError(f"Unknown benchmark: {selection}")
    return (selection,)


def run_valgrind(binary):
    result = subprocess.run(
        [
            "valgrind",
            "--tool=cachegrind",
            "--cache-sim=yes",
            "--branch-sim=yes",
            str(binary),
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=HERE,
    )
    values = {}
    for metric, pattern in METRICS.items():
        match = re.search(pattern, result.stderr)
        if match is None:
            raise RuntimeError(f"{binary.name}: Cachegrind metric missing: {metric}")
        values[metric] = int(match.group(1).replace(",", ""))
    return values


def run_runtime(binary):
    durations = []
    for _ in range(5):
        start = time.perf_counter_ns()

        subprocess.run(
            [str(binary)],
            capture_output=True,
            text=True,
            check=True,
            cwd=HERE,
        )

        elapsed_ns = time.perf_counter_ns() - start
        durations.append(elapsed_ns / 1_000_000_000)

    return sum(durations) / len(durations)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("benchmark", help="one subroutine or all")
    args = parser.parse_args()
    rows = []
    for bench in benchmarks_for(args.benchmark):
        for variant in VARIANTS:
            binary = HERE / f"cachegrind_{bench}_{variant}"
            if not binary.is_file():
                raise FileNotFoundError(f"{binary} missing: build benchmarks first")
            metrics = run_valgrind(binary)
            seconds = run_runtime(binary)
            rows.append(
                {
                    "Benchmark": bench,
                    "Variant": variant,
                    **metrics,
                    "Runtime_s": seconds,
                    "Seconds_per_instruction": seconds / metrics["I_refs"],
                }
            )
            print(f'{bench:<27} {variant:<11} I_refs={metrics["I_refs"]}')

    output = HERE / "cachegrind_results.csv"
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "Benchmark",
                "Variant",
                *METRICS,
                "Runtime_s",
                "Seconds_per_instruction",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} measurements: {output}")


if __name__ == "__main__":
    main()
