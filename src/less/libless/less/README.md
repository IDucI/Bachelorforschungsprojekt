# LESS Python Interface

This directory contains the Python interface for the LESS reference implementation.

## Project Structure

- `less.py`: Key generation, signing and verification.
- `less_subfunctions.py`: LESS subroutine wrappers.
- `less_calculations.py`: Intermediate value calculations.
- `less_calculation_result.py`: Result structures for intermediate values.
- `less_params.py`: LESS parameters.

## Usage

Build the native libraries first using `make` from `src/less/libless`.

```python
from less import Less

less = Less(path="build", category=1, target=192)

secret_key, public_key = less.keygen()
signature = less.sign(secret_key, b"Hello LESS")
valid = less.verify(public_key, b"Hello LESS", signature)
```

The toy variant only supports the subroutines not key generation, signing or verification.

## Subfunctions

The following LESS subroutines are available through `less.subfunctions`:

- `fq_inv`
- `row_mul3`
- `generator_sample`
- `monomial_sample_prikey`
- `generator_monomial_mul`

Additional functions include `expand_private_key_seeds`, `generator_rref_expand` and `monomial_inv`.

## Calculations

The calculation API reconstructs intermediate values based on LESS key generation.

```python
result = less.calculation.keygen()

seed = result.generator_sample.seed
positions = result.generator_sample.positions
```

The result also contains values for `fq_inv`, `monomial_sample_prikey` and `generator_monomial_mul`.

## Parameters

The parameters of the selected LESS configuration are available through `less.params`.