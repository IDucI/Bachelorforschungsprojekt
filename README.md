Markdown
# Bachelorforschungsprojekt
## Embedded Implementation and Evaluation of Selected Subroutines from Post-Quantum Signature Schemes (CROSS and LESS) on the STM32F4

## Overview

Post-quantum cryptography is becoming increasingly important as quantum computers pose a potential threat to the security of conventional public-key cryptographic schemes. However, deploying post-quantum cryptographic algorithms on resource-constrained embedded systems introduces practical challenges, particularly with respect to execution time and memory consumption. Furthermore, executing cryptographic operations on physical hardware raises questions about potential side-channel vulnerabilities. Investigating these aspects requires controlled access to individual cryptographic operations and a reliable setup for executing and evaluating them on embedded platforms.

This project addresses these challenges by implementing and evaluating selected subroutines from the CROSS and LESS digital signature schemes on an STM32F4 microcontroller hosted on a Riscure Piñata platform. The work focuses on individual cryptographic operations, including vector and matrix computations, data conversion, and packing routines. The selected operations are implemented in embedded C and integrated into the target firmware. A Python-based host environment, together with ChipWhisperer and the SimpleSerial V2.1 communication protocol, enables the transfer of input data, execution of selected subroutines, and retrieval of their outputs. Functional validation is performed by comparing the results obtained on the target with corresponding reference values.

In addition to functional validation, the project evaluates the execution time and memory requirements of selected operations. Runtime measurements are performed directly on the STM32F4 using the Cortex-M4 DWT cycle counter, while static stack analysis provides estimates of the memory requirements of individual functions and their call paths. These evaluations provide insights into the computational and memory constraints associated with executing cryptographic operations on the embedded platform.

Although no physical side-channel traces were acquired as part of this project, the implemented testing and evaluation setup provides a practical basis for future investigations. The results help characterize the selected operations and identify potential candidates for subsequent side-channel measurements on resource-constrained embedded systems.


## Objectives

- Understand the structure and principles of the CROSS & LESS signature scheme
- Implement selected subroutines in C
- Port the implementation to an embedded platform (STM32F4)
- Validate correctness against reference implementations
- Prepare the infrastructure for future side-channel analysis (SCA)
- Evaluate runtime and memory consumption

## Hardware Platform

- Riscure Pinata Board  
- Microcontroller: STM32F4 
- Analysis Tooling: ChipWhisperer  


## Project Structure

The project is organized into documentation and source code. The `docs` folder contains the scientific report, project proposal, and other relevant documentation.

The `src` folder contains the implementations of the investigated schemes, supporting libraries, and the provided Python environment.

```text
...Bachelorforschungsprojekt/
├── src/
│   ├── cross_round2/     (CROSS implementation)
│   ├── less/             (LESS implementation)
│   ├── libkyber/         (Supporting Kyber library)
│   └── ...
├── README.md             (Main project README)
└── ...
```

## Important

Each scheme has its own README file in its respective folder. Please read these README files carefully and follow their instructions to understand the internal project structure, setup requirements, and implementation details.

Before working with the project, activate the provided Python environment from the `src` directory:

```bash
cd .../Bachelorforschungsprojekt/src
source cw-env311/bin/activate