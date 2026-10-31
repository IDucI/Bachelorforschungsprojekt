# LESS Host Evaluation

This directory contains native benchmarks for five selected LESS subroutines and the overall key generation, signing, and verification operations.

The evaluation uses Cachegrind and Memcheck to analyze execution characteristics and memory behavior.


## Build

Build all 61 benchmark combinations:

```bash
make build-all
```

## Cachegrind

```bash
python3 collect_cachegrind.py all
```

Cachegrind collects instruction references, cache statistics and branch information.

The collection script also measures native host runtimes using Python's `time.perf_counter_ns()`.

## Memcheck

```bash
python3 collect_memcheck.py all
```

Memcheck checks memory usage and reports detected memory errors.

## Individual Subroutines

For example, to evaluate `generator_sample` across all eight parameter sets:

```bash
make build-many BENCH=generator_sample
python3 collect_cachegrind.py generator_sample
python3 collect_memcheck.py generator_sample
```

## Configuration

The evaluation covers five subroutines:

- fq_inv
- row_mul3
- generator_sample
- monomial_sample_prikey
- generator_monomial_mul

The five subroutines are benchmarked across all eight parameter sets, resulting in 40 combinations.

Key generation, signing, and verification are benchmarked across the seven official parameter sets, excluding the toy parameter set, resulting in 21 combinations.

Subroutine benchmarks use 1,000 iterations each, while key generation, signing, and verification benchmarks use 3 iterations each.

## Results

Results are written to:

- `cachegrind_results.csv`
- `memcheck_results.csv`

Run `make clean` to remove compiled benchmark binaries.