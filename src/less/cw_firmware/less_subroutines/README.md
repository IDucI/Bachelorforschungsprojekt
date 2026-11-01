# LESS Subroutine Firmware

The Pinata STM32F4 firmware runs `fq_inv`, `row_mul3`, `generator_sample`,
`monomial_sample_prikey` and `generator_monomial_mul` using SimpleSerial 2.1.

## Build

From `src/less/cw_firmware/less_subroutines`:

```bash
make clean && make
```

This builds all eight LESS configurations. To build one configuration:

```bash
make cat1_192
```

## Testing

Build the native shared libraries using `make` in `src/less/libless`.
With the board connected, run `python3 run_board_test.py` from `evaluation`.
For timing measurements, run `python3 runtime_measurement.py`.

The internal clock runs at 16 MHz; SimpleSerial operates at 230400 baud.
`generator_monomial_mul` is disabled for Categories 3 and 5 on the STM32F4
because the full generator matrix exceeds the available memory budget.

Refer to `evaluation/README.md` for seeds, categories and output files.