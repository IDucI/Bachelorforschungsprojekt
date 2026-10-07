# libcross

## Overview

libcross provides a wrapper around the reference implementation of the CROSS Round 2
submission to NIST.

https://csrc.nist.gov/projects/pqc-dig-sig/round-2-additional-signatures

It builds the supported CROSS configurations as native C libraries and provides
a Python interface to the functionality of the reference implementation.

## Supported Configurations

The CROSS implementation supports two algorithm variants, three NIST security
categories, and three optimization corners:

- **Algorithm:** R-SDP and R-SDP(G)
- **Security category:** 1, 3, and 5
- **Optimization corner:** fast, balanced, and small

This results in 18 supported configurations:

```
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
```

## Project Structure

The project is organized as follows:

```
libcross/
├── cross/                  # Python package
├── tests/                  # Test and verification code
├── variants/               # CROSS reference implementation and generated variants
├── libcross.c              # C wrapper implementation
├── libcross.h              # C wrapper interface
├── Makefile                # Main build system
├── lib_Makefile            # Build rules for the native libraries
└── pyproject.toml          # Python package configuration
```

## Building libcross

The native CROSS libraries are built from the `libcross` directory using WSL or
another Linux environment:

```
make clean
make
```

For a debug build, use:

```
make clean
make DEBUG=1
```

The default build defines `SKIP_ASSERT`, allowing signature verification to
return `0` for invalid signatures instead of terminating the process through
an assertion failure. With `DEBUG=1`, `SKIP_ASSERT` is not defined and these
assertions remain active.

## Build Output

The build creates the native libraries for each supported CROSS configuration in
the `build/` directory.

For each configuration, a shared library (`.so`) and a static library (`.a`) are
generated. The library names are suffixed with the local Linux kernel version.

## Installing libcross

After building the native libraries, `libcross` can be installed into the
currently active Python environment.

It is recommended to use a virtual environment:

```
python3 -m venv .venv
source .venv/bin/activate
```

Install `libcross` from the project directory:

```
make install
```

To verify that the installation was successful, run the following example:

```
from cross import Cross

cross = Cross()

seed_sk, pk = cross.keygen()
message = b"Hello CROSS"
signature = cross.sign(seed_sk, message)

assert cross.verify(pk, message, signature)
```

## Further Documentation

More detailed documentation is available in:

- [`cross/README.md`](cross/README.md) for the Python interface
- [`tests/README.md`](tests/README.md) for testing and verification