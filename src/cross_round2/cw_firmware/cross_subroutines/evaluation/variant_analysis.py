from pathlib import Path
import csv
import subprocess

# ============================================================================
# Configuration
# ============================================================================

base_dir = Path(__file__).resolve().parent
firmware_dir = base_dir.parent
results_dir = base_dir / "results"

output_file = results_dir / "variant_analysis.csv"

# Memory regions defined by the STM32F4 linker script:
#
# RAM:
#   Start: 0x20000000
#   Size:  0x00020000 = 128 KiB
#
# CCMRAM:
#   Start: 0x10000000
#   Size:  0x00010000 = 64 KiB
#
# These values are taken directly from the MEMORY
# definition in the linker script.
sram_size = 128 * 1024       
ccmram_size = 64 * 1024      

# ============================================================================
# Selected CROSS Subroutines
# ============================================================================

# These are the actual C function names.
#
# The "cross_" prefix is only used for the dispatcher IDs in main.c.
SELECTED_FUNCTIONS = [
    "convert_restr_vec_to_fp",
    "restr_vec_by_fp_matrix",
    "pack_fz_vec",
    "pack_fp_syn",
    "unpack_fz_vec",
    "fz_vec_sub_n",
    "fp_vec_by_fp_matrix",
    "fp_vec_by_fp_vec_pointwise",
    "fz_vec_sub_m",
    "fz_inf_w_by_fz_matrix",
    "fp_vec_by_restr_vec_scaled",
    "expand_digest_to_fixed_weight",
    "fz_dz_norm_n",
    "fz_dz_norm_m",
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
# Overall memory usage
# ============================================================================

def get_memory_usage(elf_file):
    """
    Extract overall memory usage from the ELF file.
    arm-none-eabi-size reports:
        text  data  bss  dec  hex  filename
    text + data corresponds to the amount of firmware
    stored in Flash.
    Note: The data value also includes initialized data sections such as .ccmram because .ccmram has a load address in Flash.
    """

    try:
        result = subprocess.run(
            ["arm-none-eabi-size", elf_file,], capture_output = True, text = True, check = True)
        
    except FileNotFoundError:

        raise RuntimeError("arm-none-eabi-size was not found. " "Make sure the ARM GNU toolchain is installed and in PATH.")
    
    except subprocess.CalledProcessError as error:
        print(f"Error analyzing {elf_file}:")
        print(error.stderr)
        return None

    lines = result.stdout.strip().splitlines()

    if len(lines) < 2:
        print(f"Unexpected output from arm-none-eabi-size "
            f"for {elf_file}")
        return None

    values = lines[-1].split()

    if len(values) < 6:
        print(f"Unexpected size output for {elf_file}")
        return None

    text = int(values[0])
    data = int(values[1])
    bss = int(values[2])

    return {
        "flash": text + data,
        "text": text,
        "data": data,
        "bss": bss,
    }


# ============================================================================
# Section sizes
# ============================================================================

def get_section_sizes(elf_file):
    """
    Extract relevant memory sections from the ELF file. The linker places selected large buffers into CCMRAM.
    Therefore CCMRAM is reported separately from normal SRAM. "._user_heap_stack" represents the memory reserved by the linker
    for heap and stack.
    """
    try:
        result = subprocess.run(
            ["arm-none-eabi-size", "-A", elf_file,], capture_output = True, text = True, check = True)

    except FileNotFoundError:
        raise RuntimeError("arm-none-eabi-size was not found. " "Make sure the ARM GNU toolchain is installed and in PATH.")

    except subprocess.CalledProcessError as error:
        print(f"Error analyzing sections in {elf_file}:")
        print(error.stderr)
        return {}

    sections = {".ccmram": 0, "._user_heap_stack": 0,}

    for line in result.stdout.splitlines():

        parts = line.split()

        if len(parts) < 2:
            continue

        section_name = parts[0]

        if section_name not in sections:
            continue

        try:
            sections[section_name] = int(parts[1])

        except ValueError:
            continue

    return sections

# ============================================================================
# Function sizes
# ============================================================================

def get_function_sizes(elf_file):
    """
    Extract function sizes from the ELF file. arm-none-eabi-nm reports the size of individual symbols.
    T/t symbols correspond to functions in executable sections.
    """
    try:
        result = subprocess.run(
            ["arm-none-eabi-nm", "-S", "--size-sort", elf_file,], capture_output = True, text = True, check = True)

    except FileNotFoundError:
        raise RuntimeError("arm-none-eabi-nm was not found. " "Make sure the ARM GNU toolchain is installed and in PATH.")

    except subprocess.CalledProcessError as error:
        print(f"Error analyzing functions in {elf_file}:")
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

        functions[name] = size_bytes

    return functions

# ============================================================================
# Analyze one firmware variant
# ============================================================================

def analyze_memory(elf_file):
    """
    Analyze memory usage of one ELF file.
    """
    print(f"Analyzing: {elf_file.name}")

    memory = get_memory_usage(elf_file)
    sections = get_section_sizes(elf_file)
    functions = get_function_sizes(elf_file)

    if memory is None:
        return None

    ccmram = sections.get(".ccmram", 0)

    heap_stack = sections.get("._user_heap_stack", 0)

    # ------------------------------------------------------------------------
    # SRAM calculation
    # ------------------------------------------------------------------------
    # arm-none-eabi-size includes .ccmram in "data".
    # Therefore:
    # normal SRAM allocation = (data - CCMRAM) + bss
    # This includes the linker-reserved heap/stack region.

    sram_used = (memory["data"] - ccmram + memory["bss"])

    sram_available = (sram_size - sram_used)

    ccmram_available = (ccmram_size - ccmram)

    # Application SRAM excluding reserved heap/stack
    sram_application = (sram_used - heap_stack)

    # ------------------------------------------------------------------------
    # Utilization
    # ------------------------------------------------------------------------

    flash_utilization = (memory["flash"] / (1024 * 1024) * 100)

    sram_utilization = (sram_used / sram_size * 100)

    ccmram_utilization = (ccmram / ccmram_size * 100)

    return {
        "variant": elf_file.stem,

        # Flash
        "flash": memory["flash"],
        "flash_utilization": flash_utilization,
        "text": memory["text"],
        "data": memory["data"],

        # Normal SRAM
        "sram_used": sram_used,
        "sram_available": sram_available,
        "sram_utilization": sram_utilization,

        # SRAM used by application itself
        "sram_application": sram_application,

        # CCMRAM
        "ccmram": ccmram,
        "ccmram_available": ccmram_available,
        "ccmram_utilization": ccmram_utilization,

        # Linker-reserved runtime memory
        "heap_stack": heap_stack,

        # Raw BSS
        "bss": memory["bss"],

        # Function-level information
        "functions": functions,
    }

# ============================================================================
# Save CSV
# ============================================================================

def save_results(results):
    """
    Save overall memory results to CSV.
    """
    results_dir.mkdir(parents = True, exist_ok = True)

    with open(output_file, "w", newline="", encoding="utf-8") as csv_file:

        writer = csv.writer(csv_file)

        writer.writerow([
            "variant",

            "flash_bytes",
            "flash_utilization_percent",

            "sram_used_bytes",
            "sram_available_bytes",
            "sram_utilization_percent",

            "sram_application_bytes",

            "ccmram_bytes",
            "ccmram_available_bytes",
            "ccmram_utilization_percent",

            "heap_stack_bytes",

            "text_bytes",
            "data_bytes",
            "bss_bytes",
        ])

        for result in results:

            writer.writerow([
                result["variant"],

                result["flash"],
                f"{result['flash_utilization']:.2f}",

                result["sram_used"],
                result["sram_available"],
                f"{result['sram_utilization']:.2f}",

                result["sram_application"],

                result["ccmram"],
                result["ccmram_available"],
                f"{result['ccmram_utilization']:.2f}",

                result["heap_stack"],

                result["text"],
                result["data"],
                result["bss"],
            ])

    print()
    print(f"Memory results saved to: {output_file}")

# ============================================================================
# Console output
# ============================================================================

def print_memory_summary(results):
    """
    Print a compact human-readable memory summary.
    """
    print()
    print("Memory Summary")
    print("============================================================")

    for result in results:

        print(f"\n{result['variant']}")

        print(
            f"  Flash:              "
            f"{result['flash']:>7} B "
            f"({result['flash'] / 1024:>6.1f} KiB, "
            f"{result['flash_utilization']:>5.2f} %)"
        )

        print(
            f"  SRAM used:          "
            f"{result['sram_used']:>7} B "
            f"({result['sram_used'] / 1024:>6.1f} KiB, "
            f"{result['sram_utilization']:>5.2f} %)"
        )

        print(
            f"  SRAM available:     "
            f"{result['sram_available']:>7} B "
            f"({result['sram_available'] / 1024:>6.1f} KiB)"
        )

        print(
            f"  SRAM application:   "
            f"{result['sram_application']:>7} B "
            f"({result['sram_application'] / 1024:>6.1f} KiB)"
        )

        print(
            f"  CCMRAM used:        "
            f"{result['ccmram']:>7} B "
            f"({result['ccmram'] / 1024:>6.1f} KiB, "
            f"{result['ccmram_utilization']:>5.2f} %)"
        )

        print(
            f"  CCMRAM available:   "
            f"{result['ccmram_available']:>7} B "
            f"({result['ccmram_available'] / 1024:>6.1f} KiB)"
        )

        print(
            f"  Heap/stack reserved:"
            f" {result['heap_stack']:>7} B "
            f"({result['heap_stack'] / 1024:>6.1f} KiB)"
        )

# ============================================================================
# Selected function sizes
# ============================================================================

def print_function_sizes(results):
    """
    Print sizes of the selected CROSS subroutines.
    """
    print()
    print("Selected CROSS Subroutine Sizes")
    print("============================================================")

    for result in results:

        print(f"\n{result['variant']}:")

        for function in SELECTED_FUNCTIONS:

            if function not in result["functions"]:
                continue

            size = result["functions"][function]

            print(
                f"  {function:<40} "
                f"{size:>7} bytes "
                f"({size / 1024:>6.2f} KiB)"
            )

# ============================================================================
# Main
# ============================================================================

def main():

    elf_files = find_elf_files()

    if not elf_files:
        print("No ELF files found.")
        return

    results = []

    for elf_file in elf_files:

        result = analyze_memory(elf_file)

        if result is not None:
            results.append(result)

    if not results:
        print("No memory analysis results.")
        return

    save_results(results)

    print_memory_summary(results)

    print_function_sizes(results)

    print()
    print(f"Analyzed {len(results)} firmware variants.")


if __name__ == "__main__":
    main()
