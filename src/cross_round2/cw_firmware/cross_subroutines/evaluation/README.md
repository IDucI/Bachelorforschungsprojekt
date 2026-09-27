## README

This folder contains everything needed for the performance and feasibility evaluation. It also contains the testing for the board communication, which is described at the end of the README.

## Context

The examined subroutines can be analyzed in terms of memory consumption and execution time. The evaluation allows us to:

identify potential memory and performance bottlenecks, evaluate whether the implemented components meet the constraints of the embedded platform, estimate the feasibility of executing larger parts or the full algorithm on the target device,
assess the suitability of selected operations for side-channel analysis based on execution time and expected trace length, and
measure the runtime of selected subroutines on the STM32F4 microcontroller.

## Project Location

To start the analysis, navigate to the following folder:

`.../Bachelorforschungsprojekt/src/cross_round2/cw_firmware/cross_subroutines/evaluation`

.../Bachelorforschungsprojekt/
└── src/
    └── cross_round2/
        └── cw_firmware/
            └── cross_subroutines/
                ├── evaluation/
                └── ...

## Starting the Evaluation

Run:

`make`

This creates four `.csv` files containing the results of the evaluation:

`variant_analysis.csv`: Contains the firmware-level memory consumption of the different CROSS variants. It reports the Flash, SRAM, and CCMRAM usage of each compiled firmware variant and allows the memory requirements of the different parameter sets and implementation variants to be compared.

`subroutine_analysis.csv`: Contains the code size of the selected CROSS subroutines extracted from the compiled firmware. The code size is given in bytes and represents the Flash footprint of each selected subroutine.

`stack_usage_analysis.csv`: Contains the compiler-estimated static stack usage of the selected CROSS subroutines. The values are obtained from the GCC .su files generated during compilation and indicate the stack frame size estimated for each function.

`runtime_measurement.csv`: Contains the measured execution times of the selected CROSS subroutines on the STM32F4 microcontroller. These measurements can be used to compare the runtime of the different subroutines and to assess their suitability for side-channel analysis.

The resulting `.csv`files are stored in:

`.../Bachelorforschungsprojekt/src/cross_round2/cw_firmware/cross_subroutines/evaluation/results`

.../Bachelorforschungsprojekt/
└── src/
    └── cross_round2/
        └── cw_firmware/
            └── cross_subroutines/
                ├── evaluation/
                │   └── results/
                │       └── ...

## Rebuilding the Evaluation

If files are modified and the results need to be regenerated, run:

`make clean`
`make`

## Testing the board communication

In the following folder:

`.../Bachelorforschungsprojekt/src/cross_round2/cw_firmware/cross_subroutines/evaluation`

.../Bachelorforschungsprojekt/
└── src/
    └── cross_round2/
        └── cw_firmware/
            └── cross_subroutines/
                ├── evaluation
                │   └── ...

The file `run_board_test.py` can be used to test the communication between the PC and the STM32 board as well as the correctness of the implemented subroutines.

The test workflow uses `flash.py` to flash the corresponding firmware onto the board and `board_test.py` to execute the board reference tests. For each test, randomly generated input data is sent to the board. The corresponding output is calculated using the host-side CROSS reference implementation and then compared with the output returned by the board.

If the expected and actual outputs match, the tested subroutine and the associated communication path have produced the expected result. If they do not match, the test reports a failure, which can indicate a problem with the communication, the firmware implementation, or the computation itself.

To reduce the possibility that a test passes only for a particular input, multiple rounds are executed with independently generated test inputs. Each round uses a different seed, resulting in different input data while still allowing a failing test to be reproduced using the reported seed.

To execute the file and test all 18 variants, run:

`python3/python/py run_board_test.py`

To test only a specific variant, provide the family, category, and optimization as arguments. For example:
`python3/python/py run_board_test.py RSDP 5 small`

The expected output contains a summary of the tested variants:

======================================================================
 TEST SUMMARY
======================================================================
 Pass  RSDP  Cat-5 small
 ...
======================================================================
Final result: pass
======================================================================

When all 18 variants are tested, the summary contains all 18 variants. When a specific variant is selected, only that variant is listed.

The test results are displayed in the terminal. They can also be saved as a CSV file for later analysis.



