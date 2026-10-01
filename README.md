Markdown
# Bachelorforschungsprojekt
# Embedded Implementation and Analysis of Post-Quantum Signature Schemes (CROSS,LESS so far) on STM32F4

## Overview

This project focuses on the implementation and analysis of selected components of the post-quantum signature scheme CROSS on an embedded platform.

CROSS is a code-based digital signature scheme submitted to the NIST Post-Quantum Cryptography (PQC) standardization process. It relies on the hardness of decoding problems in error-correcting codes and is designed to remain secure against quantum attacks. In addition to CROSS, other code-based signature schemes such as LESS have been proposed within the NIST additional signature call, providing alternative design approaches and performance characteristics.

CROSS aims to provide efficient digital signatures with competitive performancewhile maintaining strong security guarantees. Similar design goals can also be observed in other code-based candidates such as LESS.

The goal of this project is not to implement the full algorithm, but to adapt and analyze critical subroutines on constrained hardware. Therefore, this project focuses on implementing selected components of multiple PQC signature schemes on an embedded platform and preparing them for side-channel evaluation.

## Objectives

- Understand the structure and principles of the CROSS signature scheme
- Implement selected subroutines in C
- Port the implementation to an embedded platform (STM32F4)
- Validate correctness against reference implementations
- Prepare and perform side-channel analysis (SCA), only if time permits
- Evaluate runtime and memory consumption

## Hardware Platform

- Riscure Piñata Board  
- Microcontroller: STM32F4 
- Analysis Tooling: ChipWhisperer  

## Project Structure

The project is seperated into many areas, same folder as this README we have an docs folder `.../Bachelorforschungsprojekt/docs`
where we placed our scientific paper/report and proposal to read. If we go into the src folder we get to the important things, we can see all of the schemes which we analyzed and the libkyber libary which we get to used. 

...Bachelorforschungsprojekt/
├─ docs/                 (Folder with our documentation & other important PDFs)                           
├─ src/                     
│  ├─ cross_round2/      (CROSS scheme)   
│  ├─ cw-env311          (Virtual environment)    
│  ├─ less/              (LESS scheme)
│  ├─ libkyber/          (Libkyber libary)
│  └── ...               (Placeholder for further schemes)                      
├─ README.md             (This current README)         
│
└── ...

## Important

Each scheme has its own README file in its respective folder. Please read these README files carefully and follow their instructions to understand the internal project structure, setup requirements, and how to work with the respective implementation.

Before inspecting or working with any of the schemes, activate the provided Python environment by running the following command `source cw-env311/bin/activate` in the terminal from the specific folder:

`.../Bachelorforschungsprojekt/src`

After activating the environment, you can work with the project and its provided components.