## README
## CROSS Memory Analysis

## Purpose

This folder contains a script that generates a CSV file containing calculated memory requirements for selected CROSS operations across all supported parameter configurations.

The calculations are based on the parameter values provided by `cross_params.py` and manually defined memory-size formulas in the Python script.

The purpose is to estimate the memory required for input buffers and local output buffers of the selected operations. The resulting data provides an overview of their buffer requirements and complements the static stack analysis performed separately with STM32CubeIDE.

**Note:** This script performs formula-based memory calculations. It does not analyse the compiled firmware or determine the actual runtime stack consumption of the functions.

## Project Location

The firmware project is located at:

`...\Bachelorforschungsprojekt\src\cross_round2\cw_firmware\cross_subroutines_stack\stack`

## Input

The script uses the following Python module:

```text
libcross/cross/cross_params.py
```

It imports:

- `PARAMETER_SETS`: Defines the supported CROSS parameter configurations.
- `get_params()`: Retrieves the parameter values for each configuration.

The required parameter values include dimensions such as `N`, `K`, and `M`, element sizes, and the sizes of relevant key and signature structures.

The memory calculations themselves are defined directly in `cross_memory.py`. No compiled firmware files, HEX files, ELF files, or linker map files are required.

## Running the Script

Make sure Python 3 is installed and that the project directory structure is available.

Open a terminal in the directory containing `cross_memory.py` and execute:

```bash
python cross_memory.py
```

Alternatively, on systems where Python is invoked using `python3`:

```bash
python3 cross_memory.py
```

The script retrieves the parameter configurations, calculates the memory requirements for each supported operation, and writes the results to a CSV file.

## Output

The script generates `cross_memory.csv` in the same directory as the Python script.

The CSV file contains the following columns:

- `Variant`: CROSS parameter configuration.
- `Subroutine`: Name of the evaluated operation.
- `CCMRAM_Bytes`: Estimated size of the data stored in the shared CCMRAM buffer, such as input data and, depending on the operation, key or signature data.
- `Stack_Buffer_Bytes`: Size of the caller-allocated local output buffers, which are passed to the corresponding CROSS functions.
- `Total_Bytes`: Sum of the estimated CCMRAM and caller-allocated output buffer sizes.

The `Stack_Buffer_Bytes` values represent the sizes of the output buffers allocated by the calling firmware code. They are not the local stack requirements of the called CROSS functions.

## Scope and Limitations

The reported values represent calculated buffer sizes based on the data structures and parameter dimensions used in the implementation.

In particular:

- `CCMRAM_Bytes` represents the calculated size of the input data stored in the shared buffer.
- `Stack_Buffer_Bytes` represents the size of the local output buffer used by the corresponding operation.
- `Total_Bytes` is the sum of these two values.

These values do not represent the complete memory consumption of the firmware. In particular, the calculations do not include additional local variables, compiler-generated temporary storage, function-call overhead, or other stack usage within called functions.

## Static Stack Analysis using STM32CubeIDE

The estimated stack requirements are investigated separately using the Static Stack Analyzer in STM32CubeIDE.

### 1. Generate the Required Firmware Files

Before using the Static Stack Analyzer, the corresponding firmware files must be available. The provided Makefile automates this process.

Navigate to the directory containing the Makefile (the `stack/` directory) and execute:

```bash
make overall
```

The overall target performs the following steps:

- Checks whether the required firmware files are available for all 18 parameter configurations.
- Builds the firmware if required files are missing.
- Creates a separate output directory for each parameter configuration.
- Copies the corresponding `.elf` file and compiled object directory into the respective output directory.
- Creates additional `.su` files for selected library functions (`memcpy`, `memset`, and `memcmp`) using manually specified stack sizes derived from their assembly implementations..

The generated files are stored in the overall/ directory. Each parameter configuration has its own subdirectory:

```text
stack/
└── overall/
    ├── stack_analysis_rsdp_1_fast/
    │   ├── cross_subroutines_stack_rsdp_1_fast-PINATA.elf
    │   └── objdir-cross_subroutines_stack_rsdp_1_fast/
    │       └── ...
    ├── stack_analysis_rsdp_1_balanced/
    │   └── ...
    └── ...
```

Keeping each firmware variant in a separate directory is important because the Static Stack Analyzer uses the corresponding .su files to determine stack requirements. Mixing files from different parameter configurations could lead to incorrect analysis results.

**Note:** The Makefile checks whether the required files exist. It does not automatically detect whether an existing firmware build is outdated after source-code modifications. If the firmware has been modified, a rebuild may be required.

### 2. Open STM32CubeIDE

Open STM32CubeIDE and navigate to:

`Window → Show View → Static Stack Analyzer`

The Static Stack Analyzer view provides the interface for examining the stack requirements of the imported firmware.

### 3. Import the ELF File

For each firmware configuration, import its corresponding ELF file:

- Select `File → Import → C/C++ → STM32 Cortex-M Executable`.
- Specify the path to the .elf file in the corresponding stack_analysis_<variant> directory.
- Under MCU, select `STM32F417IGTx`.
- Complete the import process.

If a debug configuration opens after the import, simply close it. Do not start a debugging session.

### 4. Run the Static Stack Analysis

After importing the ELF file:

- Locate the imported `.elf` file in the Project Explorer.
- Select the `.elf` file.
- In the Static Stack Analyzer view, click the yellow refresh arrows to update the analysis.
- If necessary, also refresh the Build Analyzer.

The Static Stack Analyzer should then display the estimated stack usage. Inspect the available tabs and views to examine the stack usage of individual functions and their call relationships.

Repeat this procedure for the other firmware configurations to obtain their respective stack analysis results.

### Stack Analysis Results

The Static Stack Analyzer in STM32CubeIDE provides stack usage information for individual functions and their call relationships.

The exported CSV file contains the following columns:

- `variant`: CROSS parameter configuration.
- `function`: Name of the analysed function.
- `depth`: Depth of the function in the call hierarchy.
- `max_cost_bytes`: Maximum stack requirement of the function, including the stack required by called functions.
- `local_cost_bytes`: Stack requirement of the function itself, excluding its called functions.
- `type`: Stack allocation type reported by the analyzer.

The `max_cost_bytes` and `local_cost_bytes` values describe the stack requirements associated with the analysed functions. Buffers allocated by a caller and passed to a called function via pointers are not part of the called function's own stack frame. They are allocated in the caller's stack frame, if the caller allocates them locally.

The exported CSV file is stored in the `...cw_firmware\cross_subroutines_stack\stack\cross_stack_analysis_18_variants.csv`  