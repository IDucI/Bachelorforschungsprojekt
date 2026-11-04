# LESS Firmware

This directory contains the firmware for the STM32F4 Pinata using SimpleSerial 2.1.

## Project Structure

- `less_subroutines/`: Firmware for the five selected LESS subroutines.
- `less_subroutines_stack/`: Firmware for static stack analysis of LESS key generation, signing and verification.
- `hal/`, `simpleserial/` and `crypto/`: Shared firmware components.
- `Makefile.inc`: Common build settings.

## Build

The firmware projects have their own makefiles and are built separately.

Refer to `less_subroutines/README.md` for building the subroutine firmware, flashing and board tests.

Refer to `less_subroutines_stack/README.md` for the stack analysis firmware.