# README

This folder contains the testing and evaluation tools for the board communication, memory consumption and runtime measurement.

## Context

The examined subroutines can be analyzed in terms of memory consumption and runtime. The evaluation allows us to:

- identify potential memory and performance bottlenecks,
- evaluate whether the implemented components meet the constraints of the embedded platform,
- estimate the feasibility of executing larger parts or the full algorithm on the target device,
- assess the suitability of selected operations for side-channel analysis based on execution time and expected trace length, and
- measure the runtime of selected subroutines on the STM32F4 microcontroller.

## Folder Structure

The `evaluation` folder contains scripts for testing the board communication and measuring the runtime of selected operations.

- `run_board_test.py`: Tests the communication between the PC and the STM32 board and verifies the correctness of the implemented subroutines.
- `runtime_measurement.py`: Measures the execution time of selected subroutines on the STM32F4 and saves the results for further analysis.

## Testing the Board Communication and Subroutine Correctness

To start the communication, navigate to the following folder:

`.../Bachelorforschungsprojekt/src/cross_round2/cw_firmware/cross_subroutines/evaluation`

The directory structure is:

Bachelorforschungsprojekt/
└── src/
    └── cross_round2/
        └── cw_firmware/
            └── cross_subroutines/
                └── evaluation/
                    ├── run_board_test.py
                    ├── runtime_measurement.py
                    └── ...


The file `run_board_test.py` can be used to test the communication between the PC and the STM32 board as well as the correctness of the implemented subroutines.

The test workflow uses the compiled firmware together with flash.py and board_test.py. The procedure consists of three steps: checking the HEX files, flashing the firmware, and running the board reference tests.

The test uses intermediate values obtained from an actual CROSS computation. For each tested subroutine, the corresponding input intermediate is extracted from the calculations implementation and sent to the board. The subroutine is then executed on the STM32, and its output is compared with the expected intermediate output from the implementation.

Although the underlying CROSS computations use randomly generated seeds and messages, the values sent to the individual subroutines are not independently generated random test values. Instead, they are intermediate values that occur during an actual key-generation or signing computation.

To test all 18 variants, run:

`python run_board_test.py`

To test only a specific variant, provide the family, category, and optimization as arguments. For example:

`python run_board_test.py RSDP 5 small`

When all 18 variants are tested, the summary contains all 18 variants. When a specific variant is selected, only that variant is listed.

The test results are displayed in the terminal.

## Runtime Measurement

The file `runtime_measurement.py` measures the execution time of selected CROSS operations and subroutines on the STM32F4 microcontroller.

Unlike `run_board_test.py`, which focuses on communication and validation, the runtime measurement script records the number of CPU cycles required by each operation and derives the corresponding execution time. Before accepting a measurement, the script compares the firmware output with the expected output from the Python reference implementation.

## Prerequisites

- The STM32F4 board is connected to the PC.
- The required ChipWhisperer and CROSS Python dependencies are installed.
- The board is accessible through the configured serial communication interface.

## Running the Runtime Measurement

Navigate to the `evaluation` folder and run:

`python runtime_measurement.py`

By default, the script evaluates the configured parameter variants and measures each selected operation repeatedly.

To measure only a specific configuration, provide the family, category, and optimization:

`python runtime_measurement.py RSDP 5 small`

Running `python runtime_measurement.py` evaluates all configured parameter sets and measures each selected operation using the default number of repetitions.

The number of repetitions can be changed using the `--repetitions` argument. For example, to perform 20 measurements per operation:

`python runtime_measurement.py --repetitions 20`. 

The default number of repetitions is currently set to 10. This provides an initial estimate of the runtime statistics. The number of repetitions can be increased using the `--repetitions` argument if a more robust statistical evaluation is required.


### Measurement Procedure

For each selected configuration, the script prepares test cases using the Python CROSS reference implementation. It then executes the corresponding firmware subroutines on the STM32F4 and retrieves the complete output, including outputs that require multiple communication chunks.

The retrieved output is compared with the expected reference output. The cycle count and CPU clock frequency are then used to calculate the execution time.

The script records successful measurements and calculates summary statistics, including:

- number of successful and failed repetitions,
- mean and median cycle counts,
- minimum and maximum cycle counts,
- standard deviation, and
- corresponding execution-time statistics in microseconds.

The measurements are intended to characterize the runtime of the selected operations on the target microcontroller. They should be interpreted in the context of the firmware implementation, target configuration, and measurement setup.

## Results

The results are saved as a CSV file in the `results` subfolder:

evaluation/
└── results/
    └── runtime_measurement.csv

The CSV file contains the configuration metadata, operation names, repetition counts, and runtime statistics. It can be used for further analysis and comparison between parameter variants.

The measurement script also prints progress information and measurement results to the terminal. If a repetition fails, the script records the error and can continue with subsequent measurements, depending on the configured error-handling behavior.

## Notes

- Runtime measurements and memory-consumption measurements are separate evaluations and should be interpreted accordingly.
