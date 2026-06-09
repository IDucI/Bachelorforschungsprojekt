Running the Pinata CROSS Firmware with ChipWhisperer Nano

This project builds and runs the Pinata firmware for the CROSS subroutine test using a ChipWhisperer Nano.



Project Location:

The firmware project is located at:

cross_round2/cw_firmware/cross_convert_restr_vec_to_fp



Clock Setup:

The original Pinata notes mention that the external HSE clock is expected to be 16 MHz.

However, the ChipWhisperer Nano used in this setup does not provide an exact 16 MHz clock output. We tested the available clkout values and found that the closest available frequency is 15 MHz.

Therefore, the firmware is built for an external 15 MHz HSE clock.

The clock value is configured in the project Makefile:

CFLAGS += -UHSE_VALUE -DHSE_VALUE=15000000U

During compilation, the build output should show:

external clock used



Required Wiring:

Pinata -> ChipWhisperer
BOOT0  -> PDIC
RST    -> nRST
GND    -> GND
3V3    -> 3V3
PC10   -> IO1
PC11   -> IO2
PH0    -> HS2



Building the Firmware:

Build the firmware from WSL or another Linux-like environment:

cd cross_round2/cw_firmware/cross_convert_restr_vec_to_fp
make clean
./compile

The generated firmware image is:

cross_convert_restr_vec_to_fp-PINATA.hex



Flashing and Verification:

The firmware can be flashed and tested from Windows PowerShell using Python 3.12.

Run the verification script from the firmware project folder:

cd cross_round2\cw_firmware\cross_convert_restr_vec_to_fp
py -3.12 verify_pinata_external_clock.py

The script configures the ChipWhisperer Nano clock output, flashes the firmware, starts the target, and performs a SimpleSerial readback test.

Expected successful output:

clkout: 15000000.0
Verified flash OK
readback: CWbytearray(b'01 02 03')

This confirms that:

external clock output works
firmware starts correctly
UART timing is correct
SimpleSerial communication works



Adding a New CROSS Subroutine:

New CROSS subroutine can be added by copying an existing firmware project folder, for example:

cross_round2/cw_firmware/cross_convert_restr_vec_to_fp

Rename the copied folder and adapt the project Makefile if necessary, especially the TARGET name and the included source files.

The main firmware logic is implemented in main.c. For a new CROSS subroutine, include the required CROSS headers and set up the required input/output buffers there. The actual command interface is handled through SimpleSerial commands.
SimpleSerial v2.1 is used for communication between the ChipWhisperer host script and the Pinata firmware.

In the current firmware structure, the commands are used as follows:

s  - store input data in the firmware-side data buffer
b  - execute/select a subroutine
m  - return metadata or macro/configuration information
r  - response packet sent back by the firmware

For example, the host can send input data with s, trigger a CROSS subroutine with b, and then read the result from an r response.

After modifying the firmware, rebuild it from the project folder:

make clean
./compile

Then flash the generated .hex file and test it with a host script adapted to the new subroutine.