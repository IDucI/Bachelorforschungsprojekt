# README

This folder contains the firmware implementation of selected CROSS subroutines for the Riscure Pinata platform with an STM32F4 microcontroller.

The firmware is built for all 18 supported CROSS parameter and optimization variants. The generated firmware images can then be flashed onto the Pinata and verified using the ChipWhisperer. After successful flashing and verification, the firmware variants are used for the subsequent performance, memory, and feasibility evaluation.

The overall workflow is:

Build all 18 firmware variants.
Flash and verify the firmware on the Pinata.
Test the board communication and the correctness of the implemented subroutines.
Evaluate memory consumption, stack usage, code size, and runtime.

The detailed board communication tests and evaluation are documented in the README of the evaluation folder:
`.../Bachelorforschungsprojekt/src/cross_round2/cw_firmware/cross_subroutines/evaluation`

## Project Location

The firmware project is located at:
`...\Bachelorforschungsprojekt\src\cross_round2\cw_firmware\cross_subroutines`

.../Bachelorforschungsprojekt/
├── src/
│   └── cross_round2/
│       └── cw_firmware/
│           └── cross_subroutines/
│               └── ...

## Building the Firmware

Build the firmware from WSL or another Linux-like environment:
`cd .../Bachelorforschungsprojekt/src/cross_round2/cw_firmware/cross_subroutines`
`make` 
(We use make, so ./compile shouldn't be necessary)

## The generated firmware image are 18 variants of these following points

cross_rsdp_1_fast 
cross_rsdp_1_balanced 
cross_rsdp_1_small 
cross_rsdp_3_fast 
cross_rsdp_3_balanced 
cross_rsdp_3_small 
cross_rsdp_5_fast 
cross_rsdp_5_balanced 
cross_rsdp_5_small 
cross_rsdpg_1_fast 
cross_rsdpg_1_balanced 
cross_rsdpg_1_small 
cross_rsdpg_3_fast 
cross_rsdpg_3_balanced 
cross_rsdpg_3_small 
cross_rsdpg_5_fast 
cross_rsdpg_5_balanced 
cross_rsdpg_5_small

If everything worked out without an issue you can see an message with:

============================================================
All 14 variants are successfully generated!"
============================================================

## Clock Setup:

We're using the internal clk corresponding to the given README from the reference_package

## Required Wiring

Pinata -> ChipWhisperer
BOOT0  -> PDIC
RST    -> nRST
GND    -> GND
3V3    -> 3V3
PC10   -> IO1
PC11   -> IO2

## Flashing and Verification

Run the verification script from the firmware project folder:
`cd ".../Bachelorforschungsprojekt/src/cross_round2/cw_firmware/cross_subroutines"`
`python/py flash.py`

The script configures the ChipWhisperer Nano clock output, flashes the firmware, starts the target, and performs a SimpleSerial readback test.

## Expected successful output

Connecting to Scope & Target hardware...
Flashing image: cross_subroutines_...-PINATA.hex...
Detected known STMF32: STM32F40xxx/41xxx
Extended erase (0x44), this can take ten seconds or more
Attempting to program 17643 bytes at 0x8000000
STM32F Programming flash...
STM32F Reading flash...
Verified flash OK, 17643 bytes
Firmware flashing completed successfully.

## This confirms that:

-External clock output works
-Firmware starts correctly
-UART timing is correct
-SimpleSerial communication works

## In the current firmware structure, the commands are used as follows

s  - store input data in the firmware-side data buffer
b  - execute/select a subroutine
m  - return metadata or macro/configuration information
r  - response packet sent back by the firmware

For example, the host can send input data with s, trigger a CROSS subroutine with b, and then read the result from an r response.

## After modifying the firmware, rebuild it from the project folder

Execute the `make clean` command first, then build the firmware again with `make` after that we can flash .hex file again.  
Or do it in one command line with `make clean && make`.


## What can we do with the results?

The firmware build generates several build artifacts for each CROSS variant, but only the .hex files are interesting for us.

.hex files: Contain the firmware in a format suitable for programming the STM32F4 and can be used to flash the corresponding firmware variant onto the target device.

Other intermediate build files, such as .o, su and so on, are also generated during compilation but are mainly required as part of the build process and not relevant for us.

The generated results can be further analyzed in the evaluation folder:

`.../Bachelorforschungsprojekt/src/cross_round2/cw_firmware/cross_subroutines/evaluation` 

.../Bachelorforschungsprojekt/
└── src/
    └── cross_round2/
        └── cw_firmware/
            └── cross_subroutines/
                ├── evaluation/
                │   └── ...

The evaluation folder contains the tools and scripts required to analyze the generated firmware in terms of memory consumption, potential bottlenecks, runtime, and other relevant performance characteristics.

The README in the evaluation folder provides further details on how to run the evaluation and how to interpret the generated results.