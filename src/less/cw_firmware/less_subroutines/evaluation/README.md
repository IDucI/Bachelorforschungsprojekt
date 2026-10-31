# LESS Firmware Evaluation

This directory contains board tests and runtime measurements for the LESS subroutines on the STM32F4 Piñata.

## Build

The board tests compare the STM32 results against the host-side LESS reference implementation. Build the host libraries first.

From `src/less/libless`:

```bash
make
```

Build the Piñata firmware from `src/less/cw_firmware/less_subroutines`:

```bash
for category in toy cat1_192 cat1_68 cat1_45 cat3_220 cat3_102 cat5_345 cat5_137; do
    ./compile clean LESS_CATEGORY="$category"
    ./compile LESS_CATEGORY="$category"
done
```

This generates the firmware HEX files for all eight LESS variants.

## Board Tests

From `src/less/cw_firmware/less_subroutines/evaluation`:

```bash
python3 run_board_test.py
```

The runner calls `../flash.py` for each selected firmware image. The board test compares the supported LESS subroutines against the host reference implementation.

To test a single variant:

```bash
python3 run_board_test.py cat1_192
```

An optional seed can be specified to reproduce test inputs:

```bash
python3 run_board_test.py cat1_192 --seed 123456
```

The `generator_monomial_mul` subroutine is disabled on the STM32 for Categories 3 and 5 because of memory limitations.

## Runtime Measurements

Runtime measurements use the STM32F4 DWT cycle counter.

Measure all variants:

```bash
python3 runtime_measurement.py
```

Measure one variant:

```bash
python3 runtime_measurement.py cat1_192
```

The script flashes the corresponding firmware and measures each supported subroutine 10 times using the same generated input.

The results are saved to:

`results/runtime_measurement.csv`

Measurements include CPU cycles and execution times in microseconds. Serial communication is excluded from the measured subroutine execution time.

## Host Evaluation

Cachegrind and Memcheck evaluate the native LESS reference implementation on the host PC.

See `cachegrind/README.md` for build instructions and result collection.