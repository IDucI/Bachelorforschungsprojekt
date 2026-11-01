# README

This folder contains tools for testing the communication between the host system and the STM32F4 target, validating the functional correctness of selected subroutines, and measuring their execution time.

## Context


The provided tools support the following tasks:

- verify the communication between the host system and the target device,
- validate the outputs of selected subroutines against reference values from the Python CROSS implementation,
- measure the execution time of selected subroutines on the STM32F4 microcontroller, and
- collect runtime statistics for performance evaluation and to support future side-channel investigations.

Memory analysis and the broader assessment of the feasibility of executing larger algorithm components on the target platform are addressed separately in other parts of the project and are therefore outside the scope of this folder.


## Folder Structure

The `evaluation` folder contains scripts for testing the board communication and measuring the runtime of selected operations.

- `run_board_test.py`: Tests the communication between the PC and the STM32 board and verifies the correctness of the implemented subroutines.
- `runtime_measurement.py`: Measures the execution time of selected subroutines on the STM32F4 and saves the results for further analysis.


## Testing the Board Communication and Subroutine Correctness

To run the board tests, navigate to the following folder:

`.../Bachelorforschungsprojekt/src/cross_round2/cw_firmware/cross_subroutines/evaluation`

The directory structure is:

```text
Bachelorforschungsprojekt/
└── src/
    └── cross_round2/
        └── cw_firmware/
            └── cross_subroutines/
                └── evaluation/
                    ├── run_board_test.py
                    ├── runtime_measurement.py
                    └── ...
```

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

The `runtime_measurement.py` script measures the execution time of selected CROSS subroutines on the STM32F4. In addition to verifying the firmware outputs against the Python reference implementation, it records the CPU cycles required by each operation using the DWT cycle counter and derives the corresponding execution times.


## Prerequisites

- The STM32F4 board is connected to the PC.
- The compiled firmware HEX files for the evaluated configurations are available.
- The required ChipWhisperer and CROSS Python dependencies are installed.
- The board is accessible through the configured serial communication interface.


## Running the Runtime Measurement

Navigate to the `evaluation` folder and run:

If no specific configuration is provided, all configured parameter sets are evaluated.

`python runtime_measurement.py`

To measure only a specific configuration, provide the family, category, and optimization:

`python runtime_measurement.py RSDP 5 small`

The number of repetitions can be changed using the `--repetitions` argument. For example, to perform 20 measurements per operation:

`python runtime_measurement.py --repetitions 20`. 


### Measurement Procedure

The `runtime_measurement.py` script automatically measures the execution time of selected CROSS subroutines on the STM32F4 target using the ChipWhisperer Nano and SimpleSerial V2.1.

For each firmware configuration, the script generates test inputs and expected outputs using the Python CROSS reference implementation. It transfers the inputs to the target, executes the corresponding firmware subroutines, and retrieves their outputs. The returned outputs are compared with the expected reference values to verify functional correctness.

Execution cycles are measured directly on the target using the DWT cycle counter. The firmware records the cycle count around the selected function call. The host subsequently retrieves the recorded cycle count and CPU clock frequency via SimpleSerial V2.1 and calculates the execution time.

By default, each subroutine is measured ten times. The script calculates the mean, median, minimum, and maximum cycle counts, as well as the corresponding execution-time statistics and standard deviation. The median execution time is used as the primary value for evaluation.

Failed repetitions are recorded as errors, while subsequent repetitions are attempted by default.


## Results

The results are saved as a CSV file in the `results` subfolder:

```text
evaluation/
└── results/
    └── runtime_measurement.csv
```

The CSV file contains the firmware configuration, subroutine names, requested and completed repetition counts, error messages, CPU clock frequency, and the calculated cycle-count and execution-time statistics.

The measurement script also displays progress information and individual measurement results in the terminal.


