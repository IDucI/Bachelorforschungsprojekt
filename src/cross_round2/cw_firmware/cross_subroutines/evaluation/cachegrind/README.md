## README

This folder contains everything needed for the performance and feasibility evaluation towards the proposal in 2.6.

## Context

The examined subroutines can be analyzed in terms of memory consumption and execution time. The evaluation allows us to:

identify potential memory and performance bottlenecks, evaluate whether the implemented components meet the constraints of the embedded platform, estimate the feasibility of executing larger parts or the full algorithm on the target device,
assess the suitability of selected operations for side-channel analysis based on execution time and expected trace length, and
measure the runtime of selected subroutines on the STM32F4 microcontroller.

The evaluation consists of three main parts:

Cachegrind is used to analyze the computational behavior of the selected subroutines on the host system, including instruction references, data references, cache misses, branches, and branch mispredictions.
Memcheck is used to analyze dynamic memory allocation and detect memory errors and memory leaks.
STM32F4 cycle counting is used to measure the actual execution time of the selected subroutines on the target microcontroller.

## Project Location

To start the analysis, navigate to the following folder:

`.../Bachelorforschungsprojekt/src/cross_round2/cw_firmware/cross_subroutines/evaluation/cachegrind`

.../Bachelorforschungsprojekt/
└── src/
    └── cross_round2/
        └── cw_firmware/
            └── cross_subroutines/
                ├── evaluation/
                │   ├── cachegrind/
                │   │   ├── cachegrind.c
                │   │   ├── Makefile
                │   │   ├── collect_cachegrind.py
                │   │   ├── collect_memcheck.py
                │   │   └── ...
                │   └── ...
                └── ...

## Starting the Evaluation

Requirements
The host-side evaluation requires:
WSL/Linux environment, GCC and Valgrind 

Valgrind can be checked with: valgrind --version.

The STM32F4 runtime evaluation additionally requires the Riscure Pinata board and the corresponding firmware/ChipWhisperer setup.

Starting the Evaluation
1. Cachegrind:
To compile and run a specific benchmark: `make BENCH=convert_restr_vec_to_fp run`
The benchmark can be changed by setting BENCH to one of the supported subroutines.

To run the complete Cachegrind evaluation: `make`

This executes the selected benchmarks for all relevant RSDP and RSDPG parameter sets and optimization variants.
The generated Valgrind output can be analyzed using cg_annotate. The automated collection script extracts the relevant performance counters and stores them in a CSV file.

For example: `python3 collect_cachegrind.py convert_restr_vec_to_fp` for one intermediate solution 
otherwise just do: `python3 collect_cachegrind.py all` for all routines.

The results are stored in: `cachegrind_results.csv`

2. Memcheck
Memcheck is used to check the benchmark programs for memory errors, invalid accesses, and memory leaks.

For a specific benchmark: `python3 collect_memcheck.py convert_restr_vec_to_fp`

For all supported benchmarks: `python3 collect_memcheck.py all`

The results are stored in: `memcheck_results.csv`

After modifying something just execute the command `make clean && make` to rebuild the .out files and everything that is needed for the evaluation for Cachegrind. If you did the benchmarks again you can simply collect all the cachegrind files again via 
`python3 collect_cachegrind.py`

The dynamic memory allocation results describe the benchmark process as a whole. They should therefore not be interpreted as the exact RAM consumption of an individual CROSS subroutine.
The CROSS library itself does not use malloc, calloc, realloc, or free in the selected implementation paths.

3. STM32F4 Runtime Measurement
The actual execution time of the selected subroutines is measured on the STM32F4 target.
The runtime evaluation uses cycle counting to determine the number of CPU cycles required by each selected subroutine.
The target-side measurement is separate from Cachegrind:
Cachegrind: host-side performance analysis
Memcheck: host-side memory error and allocation analysis
STM32F4 cycle counting: actual target execution time

The cycle-counting setup is performed on the Riscure Pinata STM32F4 using the existing firmware and ChipWhisperer setup.
Benchmarks:
The evaluation covers the selected CROSS subroutines for the relevant parameter sets.
The common subroutines are evaluated for: RSDP andRSDPG
The RSDPG-specific subroutines are evaluated only for: RSDPG
The parameter sets cover categories 1, 3, and 5 as well as the available optimization variants (fast, balanced, and small).

Input Data:
The Cachegrind benchmarks call the CROSS subroutines directly using their C interfaces.
The benchmark inputs are deterministic test values generated locally for the respective data types and dimensions. They are used to measure the computational cost of the selected operations independently of the complete CROSS algorithm.

The board-side functional tests use inputs derived from actual CROSS reference-implementation computations. This allows the firmware implementation to be compared against the corresponding reference results.

Results:
The evaluation scripts automatically collect the measurements into CSV files.
The resulting data can be used to compare: execution cost between parameter sets, differences between optimization variants,
instruction and data access behavior, cache behavior, branch behavior, dynamic memory allocation, memory errors and leaks, and actual STM32F4 execution time.

These measurements provide the basis for identifying bottlenecks and evaluating the feasibility of the selected CROSS components on the embedded target.









