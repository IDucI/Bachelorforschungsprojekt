## README

This folder contains the firmware implementation of selected CROSS subroutines for the Riscure Piñata platform, which is based on an STM32F4 microcontroller. It also contains the firmware flashing script used by the evaluation tools.

The firmware supports 18 CROSS parameter and optimization configurations: R-SDP and R-SDP(G), each with security categories 1, 3, and 5 and the optimization variants `fast`, `balanced`, and `small`.


## Project Location

The firmware project is located at:

`...\Bachelorforschungsprojekt\src\cross_round2\cw_firmware\cross_subroutines`


## Project structure:

```text
Bachelorforschungsprojekt/
└── src/
    └── cross_round2/
        └── cw_firmware/
            └── cross_subroutines/
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


## Clock Configuration

The firmware uses the clock configuration specified in the reference package. The cycle-measurement command returns the measured cycle count and the CPU clock frequency. For the evaluated configurations, the reported CPU clock frequency is 16 MHz.
 

## Required Wiring

```text
Pinata -> ChipWhisperer
BOOT0  -> PDIC
RST    -> nRST
GND    -> GND
3V3    -> 3V3
PC10   -> IO1
PC11   -> IO2
```

Keep the ChipWhisperer and Piñata connected to the host computer and maintain the required wiring while working with this project.


## Flashing and Verification

The flashing script programs a selected firmware image onto the STM32F4 and verifies the programmed contents.

To flash a firmware image manually, navigate to the project directory: 

`cd .../Bachelorforschungsprojekt/src/cross_round2/cw_firmware/cross_subroutines`

Then run the command: `python flash.py`

Note: Manual flashing is not required before running the automated evaluation scripts. Those scripts select and flash the appropriate firmware image before performing the corresponding test or measurement.


## Expected successful output

```text
Connecting to Scope & Target hardware...
Flashing image: cross_subroutines_...-PINATA.hex...
Detected known STMF32: STM32F40xxx/41xxx
Extended erase (0x44), this can take ten seconds or more
Attempting to program 17643 bytes at 0x8000000
STM32F Programming flash...
STM32F Reading flash...
Verified flash OK, ... bytes
Firmware flashing completed successfully.
```

The exact image name and number of bytes depend on the selected configuration.
A successful flash and readback verification confirms that the firmware image was programmed and its contents were verified. 


## SimpleSerial Interface

The firmware uses SimpleSerial 2.1 (SS_VER_2_1) for communication between the host computer and the STM32F4 on the Piñata. The host communicates with the target using ChipWhisperer's SimpleSerial2 interface.

The following commands are registered in main.c:

```text
s  - Transfer input data chunks to the firmware-side shared buffer.
b  - Execute a selected CROSS subroutine.
c  - Retrieve the cycle count of the most recently executed subroutine and the reported CPU clock frequency.
```

The firmware returns result data using the r response identifier. Acknowledgements and error statuses are handled through the SimpleSerial response mechanism. The metadata command m is currently not registered.

Large inputs and outputs are transferred in multiple chunks to accommodate the communication constraints. The host reconstructs the complete output and compares it with the expected result from the host-side CROSS reference implementation.

## Generated Build Artifacts

The firmware build generates several artifacts for each CROSS configuration. The main artifact used by the flashing process is the `.hex` file, which contains the firmware image in a format suitable for programming the STM32F4.

Other generated files, such as `.elf` and `.su` files, are relevant for additional analysis. In particular, they provide the information required for the static stack analysis performed as part of this project.

The generated firmware images can be used with the evaluation scripts located in:

`.../Bachelorforschungsprojekt/src/cross_round2/cw_firmware/cross_subroutines/evaluation`

The evaluation folder contains scripts for board communication testing, functional validation of selected subroutines, and runtime measurements. Further details about these procedures are provided in the corresponding evaluation README.