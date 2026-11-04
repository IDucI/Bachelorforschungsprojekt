# libless

This directory contains the C wrapper and Python interface for the LESS reference implementation.

## Project Structure

- `less/`: Python interface, parameters and intermediate value calculations.
- `tests/`: C and Python host tests.
- `variants/`: LESS reference implementation.
- `libless.c` and `libless.h`: C wrapper.
- `Makefile` and `lib_Makefile`: Native library build.
- `pyproject.toml`: Python package configuration.

## Build

From `src/less/libless`:

```bash
make clean
make
```

This builds the toy variant and all seven official LESS parameter sets:

- `toy`
- `cat1_192`, `cat1_68`, `cat1_45`
- `cat3_220`, `cat3_102`
- `cat5_345`, `cat5_137`

The compiled libraries are saved in `build/`.

## Installation

To install the native libraries and Python package into the current environment:

```bash
make install
```

## Testing

The host tests are documented in `tests/README.md`.

The Python interface is documented in `less/README.md`.