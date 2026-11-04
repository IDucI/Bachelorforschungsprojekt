# LESS Memory and Stack Analysis

This directory contains the memory calculation and stack analysis preparation for the LESS firmware on the STM32F4 Pinata.

## Memory Calculation

From `src/less/cw_firmware/less_subroutines_stack/stack`:

```bash
python3 less_memory.py
```

The script calculates the memory requirements of the LESS subroutines using the parameters from `less_params.py`.

The results are saved to `less_memory.csv`. It includes the selected subroutines and the estimated key and signature sizes for key generation, signing and verification.

## Build

Prepare the original LESS subroutine firmware:

```bash
make subroutines
```

Prepare the separate firmware for key generation, signing and verification:

```bash
make overall
```
## Static Stack Analysis

The firmware is built using:

```bash
make subroutines
make overall
```

The ELF files and stack usage files (`.su`) are copied into the `subroutines/` and `overall/` directories.

For the analysis, open STM32CubeIDE and import the ELF file using `File -> Import -> C/C++ -> STM32 Cortex-M Executable`.

Select `STM32F417IGTx` as MCU.

Open `Window -> Show View -> Static Stack Analyzer` and refresh the analysis for each firmware variant.

The results are recorded in `less_stack_analysis.csv` using the variant, function, call depth, maximum stack cost, local stack cost and type.

`fq_inv` and `row_mul3` are inlined in the examined firmware and therefore have no separate stack entries.

The overall firmware uses enlarged memory regions for static analysis and is not intended for execution on the STM32 board.