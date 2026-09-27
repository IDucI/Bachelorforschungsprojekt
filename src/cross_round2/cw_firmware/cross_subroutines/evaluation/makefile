# Hey Emacs, this is a -*- makefile -*-
#----------------------------------------------------------------------------
#
# Makefile for Performance and Feasibility Evaluation
#
#----------------------------------------------------------------------------
#
# make
#   Runs variant analysis, subroutine analysis and runtime measurement.
#
# make variant
#   Runs the firmware-level variant analysis.
#
# make subroutine
#   Runs the selected CROSS subroutine analysis.
#
# make runtime
#   Runs the runtime measurement.
#
# make clean
#   Removes generated evaluation results.
#
#----------------------------------------------------------------------------

#----------------------------------------------------------------------------
# Global Environment Configuration
#----------------------------------------------------------------------------

SHELL := /usr/bin/bash

#----------------------------------------------------------------------------
# Configuration
#----------------------------------------------------------------------------

# Directory containing the firmware files
FIRMWARE_DIR := ..

# Directory for generated evaluation results
RESULTS_DIR := results

#----------------------------------------------------------------------------
# Evaluation
#----------------------------------------------------------------------------

.PHONY: evaluate variant subroutine runtime clean

.DEFAULT_GOAL := evaluate

# Run the complete Performance and Feasibility Evaluation
evaluate: variant subroutine stack runtime

#----------------------------------------------------------------------------
# Variant Analysis
#----------------------------------------------------------------------------

variant:
	@echo "========================================"
	@echo "Variant Analysis"
	@echo "========================================"
	@mkdir -p $(RESULTS_DIR)
	@python3 variant_analysis.py

#----------------------------------------------------------------------------
# Subroutine Analysis
#----------------------------------------------------------------------------

subroutine:
	@echo "========================================"
	@echo "Subroutine Analysis"
	@echo "========================================"
	@mkdir -p $(RESULTS_DIR)
	@python3 subroutine_analysis.py

#---------------------------------------------------------------------------- 
# Stack Usage Analysis
#---------------------------------------------------------------------------- 

stack:
	@echo "========================================"
	@echo "Stack Usage Analysis"
	@echo "========================================"
	@mkdir -p $(RESULTS_DIR)
	@python3 stack_usage_analysis.py
	
#----------------------------------------------------------------------------
# Runtime Measurement
#----------------------------------------------------------------------------

runtime:
	@echo "========================================"
	@echo "Runtime Measurement"
	@echo "========================================"
	@mkdir -p $(RESULTS_DIR)
	@python3 runtime_measurement.py

#----------------------------------------------------------------------------
# Clean
#----------------------------------------------------------------------------

clean:
	@echo "Cleaning evaluation results..."
	rm -rf $(RESULTS_DIR)

