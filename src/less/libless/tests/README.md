# LESS Host Tests

This directory contains host tests for the seven official LESS parameter sets.

The C test generates reference JSON files containing compressed secret keys and generator matrix products. The Python test compares these reference values with the results reconstructed using the LESS Python wrappers.

The signing tests check successful signature verification and rejection of modified messages, different signatures and incorrect public keys.

## Running the Tests


From the `src/less/libless` directory:

```bash
make
make -C tests
PYTHONPATH=. python3 tests/test_less.py
PYTHONPATH=. python3 tests/test_intermediates.py
python3 -m tests.sign
```

`make` builds the native LESS libraries.

`make -C tests` compiles and executes `test_less.c`, generating reference JSON files for all seven official parameter sets.

`test_less.py` compares the reconstructed generator matrix products against these reference values.

`test_intermediates.py` validates key-generation intermediate values used by the board evaluation.

`tests.sign` and `tests.verify` test key generation, signing and verification for all seven official parameter sets.

The toy variant is not included in the full key generation and signature tests.

## Cleanup

```bash
make -C tests clean
```