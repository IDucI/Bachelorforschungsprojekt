# README

Running the Pinata CROSS Firmware with ChipWhisperer Nano.
This project builds and runs the Pinata firmware for the CROSS subroutine test using a ChipWhisperer Nano.


## Project Location:

The firmware project is located at:
`...\Bachelorforschungsprojekt\src\cross_round2\cw_firmware\cross_subroutines`

## Clock Setup:

We're using the internal clk corresponding to the given README from the reference_package


## Required Wiring:

Pinata -> ChipWhisperer
BOOT0  -> PDIC
RST    -> nRST
GND    -> GND
3V3    -> 3V3
PC10   -> IO1
PC11   -> IO2
PH0    -> HS2 -> This isn't necessary anymore, because we don't use an external clock anymore


## Building the Firmware:

Build the firmware from WSL or another Linux-like environment:
`cd .../Bachelorforschungsprojekt/src/cross_round2/cw_firmware/cross_subroutines`
`make PLATFORM=PINATA MCU_CLK=INT -j all` 
(We use make, so ./compile shouldn't be necessary)

## The generated firmware image are 18 variants of these following points:

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

-> We're getting the .hex- .elf- .map- .lss- .sym- .bin- .eep-files, where only the .hex is pretty interesting for us. This process will take around 3 to 4 minutes 

## Flashing and Verification: 

The firmware can be flashed and tested from Windows PowerShell using Python 3.12.
Run the verification script from the firmware project folder:
`cd "...\Bachelorforschungsprojekt\src\cross_round2\cw_firmware\cross_subroutines"`
`python/py flash.py`
-> The process will take around 10 minutes 

The script configures the ChipWhisperer Nano clock output, flashes the firmware, starts the target, and performs a SimpleSerial readback test.
## Expected successful output:

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

============================================================
 All available firmware sets successfully flashed and verified
============================================================


## This confirms that:

-External clock output works
-Firmware starts correctly
-UART timing is correct
-SimpleSerial communication works


## In the current firmware structure, the commands are used as follows:

s  - store input data in the firmware-side data buffer
b  - execute/select a subroutine
m  - return metadata or macro/configuration information
r  - response packet sent back by the firmware
For example, the host can send input data with s, trigger a CROSS subroutine with b, and then read the result from an r response.


## After modifying the firmware, rebuild it from the project folder:

Execute the `make clean` command first, then build the firmware again with `make PLATFORM=PINATA MCU_CLK=INT -j all`. After that we can flash the generated 
.hex file again.
