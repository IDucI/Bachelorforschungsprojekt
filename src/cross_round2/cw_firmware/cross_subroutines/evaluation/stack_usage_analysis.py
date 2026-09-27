from pathlib import Path
import csv

# ============================================================================
# Configuration
# ============================================================================

base_dir = Path(__file__).resolve().parent
firmware_dir = base_dir.parent
results_dir = base_dir / "results"

output_file = results_dir / "stack_usage_analysis.csv"

# ============================================================================
# Selected CROSS Subroutines
# ============================================================================

RSDP_FUNCTIONS = [
    "convert_restr_vec_to_fp",
    "restr_vec_by_fp_matrix",
    "pack_fz_vec",
    "pack_fp_syn",
    "unpack_fz_vec",
    "fz_vec_sub_n",
    "fp_vec_by_fp_matrix",
    "fp_vec_by_fp_vec_pointwise",
    "fp_vec_by_restr_vec_scaled",
    "expand_digest_to_fixed_weight",
    "fz_dz_norm_n",
    "expand_pk",
    "expand_sk",
]

RSDPG_FUNCTIONS = [
    "fz_inf_w_by_fz_matrix",
    "fz_vec_sub_m",
    "fz_dz_norm_m",
    "pack_fz_rsdp_g_vec",
    "expand_pk",
    "expand_sk",
]

# ============================================================================
# Find .su files
# ============================================================================

def find_su_files():
    """
    Find all compiler-generated stack-usage files.
    """
    su_files = sorted(firmware_dir.rglob("*.su"))

    if not su_files:
        print(f"No .su files found in {firmware_dir}")

    return su_files

# ============================================================================
# Parse one .su file
# ============================================================================

def parse_su_file(su_file):
    """
    Parse a GCC .su file. Typical format:
        file.c:function_name  80  static
    Returns:
        {
            "function_name": {
                "stack_bytes": 80,
                "qualifier": "static"
            }
        }
    """

    functions = {}

    try:
        with open(su_file, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()

                if not line:
                    continue

                parts = line.split("\t")

                if len(parts) < 2:
                    continue

                function_location = parts[0]
                stack_size = parts[1]

                qualifier = parts[2] if len(parts) >= 3 else ""

                # Function name is after the last colon.
                function_name = function_location.rsplit(":", 1)[-1]

                try:
                    stack_bytes = int(stack_size)
                except ValueError:
                    continue

                functions[function_name] = {
                    "stack_bytes": stack_bytes,
                    "qualifier": qualifier,
                }

    except OSError as error:
        print(f"Error reading {su_file}:")
        print(error)
        return {}

    return functions

# ============================================================================
# Determine firmware variant
# ============================================================================

def get_variant_from_path(su_file):
    """
    Determine the firmware variant from the directory structure. Expected example:
        objdir-cross_subroutines_rsdp_1_balanced/
            main.su
            libcross.su
            ...
    """
    for parent in su_file.parents:
        name = parent.name

        if name.startswith("objdir-cross_subroutines_"):
            return name.replace("objdir-", "")

    return None

# ============================================================================
# Analyze selected subroutines
# ============================================================================

def analyze_subroutines(su_files):
    """
    Analyze selected CROSS subroutines from all .su files. Keep only one entry per variant and subroutine.
    Prefer CROSS.su over other .su files if duplicates occur.
    """
    results = {}

    for su_file in su_files:

        variant = get_variant_from_path(su_file)

        if variant is None:
            continue

        if "rsdpg" in variant.lower():
            selected_functions = RSDPG_FUNCTIONS
        else:
            selected_functions = RSDP_FUNCTIONS

        functions = parse_su_file(su_file)

        for function in selected_functions:

            if function not in functions:
                continue

            key = (variant, function)

            new_result = {
                "variant": variant,
                "subroutine": function,
                "stack_usage_bytes": functions[function]["stack_bytes"],
                "source_file": su_file.name,
            }

            if key not in results:
                results[key] = new_result

            elif results[key]["source_file"] != "CROSS.su" and su_file.name == "CROSS.su":
                results[key] = new_result

    return list(results.values())

# ============================================================================
# Save CSV
# ============================================================================

def save_results(rows):
    """
    Save subroutine-level stack-usage results to CSV.
    """
    results_dir.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", newline = "", encoding = "utf-8") as csv_file:

        writer = csv.writer(csv_file)

        writer.writerow([
            "variant",
            "subroutine",
            "stack_usage_bytes",
            "source_file",
        ])

        for row in rows:
            writer.writerow([
                row["variant"],
                row["subroutine"],
                row["stack_usage_bytes"],
                row["source_file"],
            ])

    print()
    print(f"Stack-usage results saved to: {output_file}")

# ============================================================================
# Console output
# ============================================================================

def print_summary(rows):
    """
    Print a compact summary of the selected subroutine stack usage.
    """
    print()
    print("Selected CROSS Subroutine Stack Usage")
    print("=" * 70)

    current_variant = None

    for row in rows:

        if row["variant"] != current_variant:
            current_variant = row["variant"]
            print(f"\n{current_variant}:")

        print(
            f"  {row['subroutine']:<40} "
            f"{row['stack_usage_bytes']:>7} B"
        )

# ============================================================================
# Main
# ============================================================================

def main():

    su_files = find_su_files()

    if not su_files:
        print("No .su files found.")
        return

    rows = analyze_subroutines(su_files)

    if not rows:
        print("No selected CROSS subroutine stack-usage results found.")
        return

    save_results(rows)
    print_summary(rows)

    print()
    print(f"Total selected subroutine entries: {len(rows)}")


if __name__ == "__main__":
    main()