from pathlib import Path
import csv
import subprocess

# ============================================================================
# Configuration
# ============================================================================

base_dir = Path(__file__).resolve().parent
firmware_dir = base_dir.parent
results_dir = base_dir / "results"

output_file = results_dir / "subroutine_analysis.csv"

# ============================================================================
# Selected CROSS subroutines
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
# Find ELF files
# ============================================================================

def find_elf_files():
    """
    Find all compiled CROSS firmware ELF files.
    """
    elf_files = sorted(firmware_dir.glob("cross_subroutines_*-PINATA.elf"))

    if not elf_files:
        print(f"No ELF files found in {firmware_dir}")

    return elf_files

# ============================================================================
# Function sizes
# ============================================================================

def get_function_sizes(elf_file):
    """
    Extract function sizes from the ELF file.
    arm-none-eabi-nm reports the address, size, symbol type and name
    of symbols. T/t symbols correspond to functions in executable sections.
    """
    try:
        result = subprocess.run(
            [
                "arm-none-eabi-nm",
                "-S",
                "--size-sort",
                elf_file,
            ],
            capture_output = True,
            text = True,
            check = True,
        )

    except FileNotFoundError:
        raise RuntimeError(
            "arm-none-eabi-nm was not found. "
            "Make sure the ARM GNU toolchain is installed and in PATH."
        )

    except subprocess.CalledProcessError as error:
        print(f"Error analyzing {elf_file}:")
        print(error.stderr)
        return {}

    functions = {}

    for line in result.stdout.splitlines():
        parts = line.split()

        if len(parts) < 4:
            continue

        address, size, symbol_type, name = parts[:4]

        # T/t = function in executable code
        if symbol_type not in ("T", "t"):
            continue

        try:
            size_bytes = int(size, 16)
        except ValueError:
            continue

        functions[name] = {
            "address": address,
            "size": size_bytes,
        }

    return functions

# ============================================================================
# Analyze one firmware variant
# ============================================================================

def analyze_subroutines(elf_file):
    """
    Analyze the selected CROSS subroutines of one firmware variant.
    """
    functions = get_function_sizes(elf_file)

    if not functions:
        return []

    # Select subroutines according to the implementation variant
    if "rsdpg" in elf_file.stem.lower():
        selected_functions = RSDPG_FUNCTIONS
    else:
        selected_functions = RSDP_FUNCTIONS

    rows = []

    for function in selected_functions:
        if function not in functions:
            continue

        rows.append({
            "variant": elf_file.stem,
            "subroutine": function,
            "address": functions[function]["address"],
            "code_size_bytes": functions[function]["size"],
        })

    return rows

# ============================================================================
# Save CSV
# ============================================================================

def save_results(rows):
    """
    Save subroutine-level code-size results to CSV.
    """
    results_dir.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", newline = "", encoding = "utf-8") as csv_file:
        writer = csv.writer(csv_file)

        writer.writerow([
            "variant",
            "subroutine",
            "address",
            "code_size_bytes",
        ])

        for row in rows:
            writer.writerow([
                row["variant"],
                row["subroutine"],
                row["address"],
                row["code_size_bytes"],
            ])

    print()
    print(f"Subroutine results saved to: {output_file}")

# ============================================================================
# Console output
# ============================================================================

def print_summary(rows):
    """
    Print a compact summary of the selected subroutine sizes.
    """
    print()
    print("Selected CROSS Subroutine Code Sizes")
    print("=" * 70)

    current_variant = None

    for row in rows:
        if row["variant"] != current_variant:
            current_variant = row["variant"]
            print(f"\n{current_variant}:")

        print(
            f"  {row['subroutine']:<40} "
            f"{row['code_size_bytes']:>7} B "
            f"({row['code_size_bytes'] / 1024:>6.2f} KiB)"
        )

# ============================================================================
# Main
# ============================================================================

def main():
    elf_files = find_elf_files()

    if not elf_files:
        print("No ELF files found.")
        return

    rows = []

    for elf_file in elf_files:
        rows.extend(analyze_subroutines(elf_file))

    if not rows:
        print("No selected CROSS subroutine results found.")
        return

    save_results(rows)
    print_summary(rows)

    print()
    print(f"RSDP selected subroutines: {len(RSDP_FUNCTIONS)}")
    print(f"RSDPG selected subroutines: {len(RSDPG_FUNCTIONS)}")
    print(f"Total selected subroutine entries: " f"{len(RSDP_FUNCTIONS) + len(RSDPG_FUNCTIONS)}")

if __name__ == "__main__":
    main()
