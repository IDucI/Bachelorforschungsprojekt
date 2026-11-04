# LESS Stack Analysis Firmware

This directory contains a copy of the LESS subroutine firmware with additional operations for key generation, signing and verification.

The additional operations are for the static stack analysis.

## Build

From `src/less/cw_firmware/less_subroutines_stack`:

```bash
make clean && make
```

This builds all seven official LESS configurations. To build one configuration:

```bash
make cat1_192
```

## Stack Analysis

The firmware is used to analyse the stack requirements of LESS key generation, signing and verification with STM32CubeIDE.

The original subroutine firmware remains in `../less_subroutines` and is not modified.

Refer to `stack/README.md` for the memory calculations and Static Stack Analyzer instructions.
