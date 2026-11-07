## README

This folder contains the firmware implementation of selected CROSS subroutines, together with entry points for the three high-level operations: key generation, signing, and verification.

The primary purpose of this folder is to analyse the memory and stack requirements of the implemented operations on the target platform. The keygen, sign, and verify entry points are additionally included for stack analysis. They are not intended to provide complete, functionally validated key generation, signing, or verification workflows.

An additional README is available in the `...\Bachelorforschungsprojekt\src\cross_round2\cw_firmware\cross_subroutines_stack\stack` subfolder. It provides further details on the stack analysis performed using the firmware built from this directory.


## Project Location

The firmware project is located at:

`...\Bachelorforschungsprojekt\src\cross_round2\cw_firmware\cross_subroutines_stack`


## Project structure:

```text
Bachelorforschungsprojekt/
└── src/
    └── cross_round2/
        └── cw_firmware/
            └── cross_subroutines_stack/
                ├── evaluation/
                ├── flash.py
                └── ...
```


## Building the Firmware

Build the firmware from WSL or another Linux-like environment.
Navigate to the project directory:

`cd .../Bachelorforschungsprojekt/src/cross_round2/cw_firmware/cross_subroutines`

Build the firmware:

`make`

The project uses make to compile the firmware.

To perform a clean rebuild after modifying the firmware:

`make clean && make`

## Build Configurations

The build covers the following 18 firmware configurations:

```text
cross_subroutines_rsdp_1_fast
cross_subroutines_rsdp_1_balanced
cross_subroutines_rsdp_1_small
cross_subroutines_rsdp_3_fast
cross_subroutines_rsdp_3_balanced
cross_subroutines_rsdp_3_small
cross_subroutines_rsdp_5_fast
cross_subroutines_rsdp_5_balanced
cross_subroutines_rsdp_5_small

cross_subroutines_rsdpg_1_fast
cross_subroutines_rsdpg_1_balanced
cross_subroutines_rsdpg_1_small
cross_subroutines_rsdpg_3_fast
cross_subroutines_rsdpg_3_balanced
cross_subroutines_rsdpg_3_small
cross_subroutines_rsdpg_5_fast
cross_subroutines_rsdpg_5_balanced
cross_subroutines_rsdpg_5_small
```

The generated HEX filenames follow the naming convention:

cross_subroutines_<family>_<category>_<variant>-PINATA.hex

For example: `cross_subroutines_rsdp_1_fast-PINATA.hex`

A successful build should finish without compilation or linking errors. The build output may report that all the firmware generation is completed for all 18 configurations.