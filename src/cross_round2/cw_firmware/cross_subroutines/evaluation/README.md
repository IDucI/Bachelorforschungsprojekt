## README

This folder contains the testing for the board communication.

## Context

The examined subroutines can be analyzed in terms of memory consumption and execution time. The evaluation allows us to:

identify potential memory and performance bottlenecks, evaluate whether the implemented components meet the constraints of the embedded platform, estimate the feasibility of executing larger parts or the full algorithm on the target device,
assess the suitability of selected operations for side-channel analysis based on execution time and expected trace length, and
measure the runtime of selected subroutines on the STM32F4 microcontroller.

## Testing the board communication

To start the communication, navigate to the following folder:

`.../Bachelorforschungsprojekt/src/cross_round2/cw_firmware/cross_subroutines/evaluation`

.../Bachelorforschungsprojekt/
└── src/
    └── cross_round2/
        └── cw_firmware/
            └── cross_subroutines/
                ├── evaluation
                │   └── ...

The file `run_board_test.py` can be used to test the communication between the PC and the STM32 board as well as the correctness of the implemented subroutines.

The test workflow uses the firmware previously flashed during the flashing and verification procedure. If the firmware has not been flashed yet, or if the board has been disconnected from the PC and the firmware needs to be restored, go back to the cross_subroutines folder: `cd ".../Bachelorforschungsprojekt/src/cross_round2/cw_firmware/cross_subroutines"`, and follow the flashing and verification procedure described in its README. If the firmware already has been flashed you can ignore this part then.

The test uses intermediate values obtained from an actual CROSS computation. For each tested subroutine, the corresponding input intermediate is extracted from the calculations implementation and sent to the board. The subroutine is then executed on the STM32 and its output is compared with the corresponding expected intermediate output from the implementation.

Although the underlying CROSS computations use randomly generated seeds and messages, the values sent to the individual subroutines are not independently generated random test values. They are intermediate values that occur during an actual key-generation or signing computation.

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



