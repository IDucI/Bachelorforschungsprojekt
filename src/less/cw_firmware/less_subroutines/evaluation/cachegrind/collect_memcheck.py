import argparse
import csv
import re
import subprocess

from collect_cachegrind import HERE, VARIANTS, benchmarks_for

FIELDS = (
    "Allocs",
    "Frees",
    "Bytes_Allocated",
    "Bytes_In_Use",
    "Blocks_In_Use",
    "Errors",
)


def parse_number(value):
    return int(value.replace(",", ""))


def parse_memcheck(output):
    result = {
        "Allocs": None,
        "Frees": None,
        "Bytes_Allocated": None,
        "Bytes_In_Use": None,
        "Blocks_In_Use": None,
        "Errors": None,
    }

    heap = re.search(
        r"total heap usage:\s*([\d,]+) allocs,\s*([\d,]+) frees,\s*([\d,]+) bytes allocated",
        output,
    )

    if heap:
        result["Allocs"] = parse_number(heap.group(1))
        result["Frees"] = parse_number(heap.group(2))
        result["Bytes_Allocated"] = parse_number(heap.group(3))

    remaining = re.search(
        r"in use at exit:\s*([\d,]+) bytes in\s*([\d,]+) blocks", output
    )

    if remaining:
        result["Bytes_In_Use"] = parse_number(remaining.group(1))
        result["Blocks_In_Use"] = parse_number(remaining.group(2))

    errors = re.search(r"ERROR SUMMARY:\s*([\d,]+) errors", output)

    if errors:
        result["Errors"] = parse_number(errors.group(1))

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("benchmark", help="one benchmark or all")
    args = parser.parse_args()
    benchmarks = benchmarks_for(args.benchmark)

    rows = []
    for bench in benchmarks:
        for variant in VARIANTS:
            binary = HERE / f"cachegrind_{bench}_{variant}"
            if not binary.is_file():
                print(f"ERROR: Binary not found: {binary}")
                continue
            process = subprocess.run(
                [
                    "valgrind",
                    "--tool=memcheck",
                    "--leak-check=full",
                    "--show-leak-kinds=all",
                    str(binary),
                ],
                capture_output=True,
                text=True,
                cwd=HERE,
            )
            if process.returncode != 0:
                print(
                    f"ERROR: Memcheck failed for {binary} "
                    f"(exit code {process.returncode})"
                )
                continue
            result = parse_memcheck(process.stderr)
            rows.append({"Benchmark": bench, "Variant": variant, **result})
            print(f'{bench:<27} {variant:<11} errors={result["Errors"]}')

    output = HERE / "memcheck_results.csv"
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Benchmark", "Variant", *FIELDS])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} measurements: {output}")


if __name__ == "__main__":
    main()
