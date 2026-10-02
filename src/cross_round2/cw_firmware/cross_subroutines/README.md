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

-> We're getting the .hex- .elf- .map- .lss- .sym- .bin- .eep-files, where only the .hex is pretty interesting for us. This process will take around 6 to 7 minutes. 
If everything worked out without an issue you can see an message with:

============================================================
All 18 variants are successfully generated!"
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
PH0    -> HS2 -> This isn't necessary anymore, because we don't use an external clock anymore

## Flashing and Verification

The firmware must be flashed and verified before performing the board communication tests.

Important: Do not unplug the board or the ChipWhisperer from the PC after flashing. Otherwise, the firmware may need to be flashed again before communication with the board can be established.

Run the verification script from the firmware project folder:
`cd ".../Bachelorforschungsprojekt/src/cross_round2/cw_firmware/cross_subroutines"`
`python/py flash.py`
-> The process will take around 10 minutes 

The script configures the ChipWhisperer Nano clock output, flashes the firmware, starts the target, and performs a SimpleSerial readback test.

## Expected successful output

Flashing target with: cross_subroutines_'...'-PINATA.hex...
Detected known STMF32: STM32F40xxx/41xxx
Extended erase (0x44), this can take ten seconds or more
Attempting to program 17595 bytes at 0x8000000
STM32F Programming flash...
STM32F Reading flash...
Verified flash OK, 17595 bytes
Flashing successful!
Readback: CWbytearray(b'01 02 03')
OK: SimpleSerial responsiveness verified.

-> In the end we should get this following message in the terminal, when all the 18 variants are flashed successfully:

=====================================================================
 All available firmware sets successfully flashed & verified 
=====================================================================

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

Don't do `make clean && make`, because The make clean doesn't catch all subfolders at once. When rm -rf objdir-* is executed, the system sends the delete command to the file system. With quick calls (or under WSL/Windows), the file system sometimes only frees the directories a few milliseconds later, even though Bash has already started the next command (make).
The following `make` then sees for example for 7 variants, the .hex files or subfolders still exist and are up-to-date. It thinks then I don’t need to rebuild them. So it only builds the 11 variants that had already been deleted.


## What can we do with the results?

The firmware build generates several build artifacts for each CROSS variant, including .elf, .hex, and .su files.

.elf files: Contain the compiled firmware together with symbol and section information. They are used by the evaluation scripts to analyze firmware memory consumption and the code size of selected subroutines.

.hex files: Contain the firmware in a format suitable for programming the STM32F4 and can be used to flash the corresponding firmware variant onto the target device.

.su files: Are generated by the compiler when stack-usage analysis is enabled. They contain compiler-estimated static stack usage information for individual functions and are used by the stack_usage_analysis.py script.

Other intermediate build files, such as .o object files, are also generated during compilation but are mainly required as part of the build process.

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