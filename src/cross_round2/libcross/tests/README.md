# Tests

## Overview

The tests validate libcross at three levels: the high-level API, the calculation
API, and the subfunction wrappers used by CROSS key generation and signing.

Key generation and signing are reconstructed step by step using the Python
subfunction wrappers. Intermediate results are checked against the values
recorded by the calculation API, while the resulting public keys and signatures
are compared with reference data produced by the C implementation.

As an additional end-to-end check, keys and signatures generated through both
Python APIs are passed to the original C `CROSS_verify()` implementation.

## Test Workflow
First, `generate_c_test_data.c` creates reference data for each supported CROSS
configuration. It performs key generation and signing based on the C reference
implementation and stores the message, secret key seed, public key, root seed,
salt, and resulting signature in a JSON file.

Next, `test_cross.py` uses this data to reconstruct key generation and signing
step by step with the Python subfunction wrappers. The intermediate values are
compared with the values recorded by the calculation API, while the reconstructed
public key and signature are compared with the C-generated reference data.

The test script then generates new key pairs and signatures independently
through both the high-level and calculation APIs. The generated values are
stored in `c_verify_py.json` and passed to `verify_py.c`, which verifies the
signatures using the original C `CROSS_verify()` implementation.

## Running the Tests

Before running the tests, the native libraries must first be built from the
`libcross` directory. See the [main README](../README.md) for the build
instructions.

Run the complete test suite from the `tests/` directory:

```
make clean
make test
```

If `libcross` was built with `DEBUG=1`, run the tests with the same setting:

```
make clean
make test DEBUG=1
```

The `test` target executes the complete test workflow in the required order for
all supported CROSS configurations.