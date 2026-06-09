# README

this folder contains everything needed to build the software for the pinata.

`simpleserial-databuffer` is an example project. You can copy this and rename it (also inside the makefile) to create a new project to implement a new thing. `crypto`, `hal` and `simpleserial` should not be changed in general. They are the library functions that are used in any project. You could add the new crypto to the `crypto` folder if you really want to figure it out. Otherwise just add it to the individual projects. Looking inside `simpleserial` is useful when trying to figure out how the serial communication works. Please use `SS_VER_2_1` for the implementation. It is more advanced and allows for more data. The documentation for simpleserial can be found [here](https://chipwhisperer.readthedocs.io/en/latest/simpleserial.html).

Nested inside the `hal` folder is the `pinata` folder. This contains another `readme` which explains how to use the pinata with a chipwhisperer.

`compile` calls `make` with the required options. You can use `make` itself if you want.

## Compiler requirements

- The compiler is: `arm-none-eabi-gcc`
- ST link tools are found in: `stlink-tools` [package github](https://github.com/stlink-org/stlink)

<!-- ## debugging

It is possible to debug a target using `gdb`.

*note: sure it is possible but it requires an external programmer instead of the chipwhisperer.
-->
