# Hey Emacs, this is a -*- makefile -*-
#----------------------------------------------------------------------------
#
# Makefile for ChipWhisperer SimpleSerial-AES Program
#
#----------------------------------------------------------------------------
# On command line:
#
# make all = Make software.
#
# make clean = Clean out built project files.
#
# make filename.s = Just compile filename.c into the assembler code only.
#
# make filename.i = Create a preprocessed source file for use in submitting
#                   bug reports to the GCC project.
#
# To rebuild project do "make clean" then "make all".
#----------------------------------------------------------------------------

# Global Environment Configuration: 
#
# Explicitly sets the shell to Bash so that 'echo -e' and subshells run smoothly
SHELL := /usr/bin/bash

# Guaranteed clean console output with -j
#
# Parallel build setup (18 jobs here) with line-synchronized output
MAKEFLAGS += -j --output-sync=line

# Default values for platform & clock
#
# Conditional assignment (?=) sets defaults if not specified externally
PLATFORM ?= PINATA
MCU_CLK  ?= INT

# Dynamically extracts current directory name to build unique targets
DIRNAME := $(notdir $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST))))))

# =============================================================================
# VARIANTS BUILD LOOP (Executed when no "BUILD_SUB_VARIANT" variable exists)
# =============================================================================

ifndef BUILD_SUB_VARIANT

# Sets 'hex' as the default target when simply running 'make'
.DEFAULT_GOAL := hex

# List of all 18 CROSS parameter set combinations
HEXNAMES = \
    cross_rsdp_1_fast \
    cross_rsdp_1_balanced \
    cross_rsdp_1_small \
    cross_rsdp_3_fast \
    cross_rsdp_3_balanced \
    cross_rsdp_3_small \
    cross_rsdp_5_fast \
    cross_rsdp_5_balanced \
    cross_rsdp_5_small \
    cross_rsdpg_1_fast \
    cross_rsdpg_1_balanced \
    cross_rsdpg_1_small \
    cross_rsdpg_3_fast \
    cross_rsdpg_3_balanced \
    cross_rsdpg_3_small \
    cross_rsdpg_5_fast \
    cross_rsdpg_5_balanced \
    cross_rsdpg_5_small

# Mark targets that do not represent physical output files as PHONY
.PHONY: hex all clean $(HEXNAMES)

all: hex

hex: $(HEXNAMES)
	@echo "--------------------------------------------------------"
	@echo " Firmware generation completed for all 18 configurations"
	@echo " covering 14 CROSS subroutine implementations"
	@echo "--------------------------------------------------------"

# Main build loop: Splits the target name into macro flags 
#
# and calls itself recursively for each individual variant.
#
# Parses target string (e.g. cross_rsdp_1_fast), converts values into C-Preprocessor Macros, 
#
# and creates a recursive sub-make execution for the specific sub-variant.
$(HEXNAMES):
	@RAW_VAR=$$(echo $@ | cut -d'_' -f2); \
	if [ "$$RAW_VAR" = "rsdpg" ]; then VAR="RSDPG"; else VAR="RSDP"; fi; \
	CAT=$$(echo $@ | cut -d'_' -f3); \
	OPT_RAW=$$(echo $@ | cut -d'_' -f4); \
	if [ "$$OPT_RAW" = "fast" ]; then OPT="SPEED"; elif [ "$$OPT_RAW" = "small" ]; then OPT="SIG_SIZE"; else OPT="BALANCED"; fi; \
	CLEAN_NAME=$$(echo $@ | sed 's/^cross_//'); \
	FULL_TARGET="$(DIRNAME)_$$CLEAN_NAME"; \
	echo "===== Building Firmware Variant: $$FULL_TARGET ====="; \
	mkdir -p "objdir-$$FULL_TARGET"; \
	$(MAKE) --no-print-directory \
		BUILD_SUB_VARIANT=1 \
    	TARGET=$$FULL_TARGET \
    	OBJDIR="objdir-$$FULL_TARGET" \
    	SS_VER=SS_VER_2_1 \
    	MCU_CLK=$(MCU_CLK) \
    	PLATFORM=$(PLATFORM) \
    	CRYPTO_TARGET=NONE \
    	EXTRA_CFLAGS="-D$$VAR -DCATEGORY_$$CAT -D$$OPT" \
    	all || exit 1; \
	echo "===== Finished Firmware Variant: $$FULL_TARGET ====="	
	
clean:
	@echo "Cleaning up all build artifacts and variant directories..."
	rm -rf objdir-*
	rm -f *.hex *.elf *.map *.su *.lst *.o *.lss *.sym *.bin *.eep
	@echo "Clean completed!"

# =============================================================================
# SINGLE VARIANT BUILD LOGIC (Only called in the sub-make)
# =============================================================================

else

ifeq ($(HIGH_SPEED_BAUD),1)
CFLAGS += -DHIGH_SPEED_UART_BAUD=921600U
endif

SS_VER::=SS_VER_2_1
# $(error, VAR is $(SS_VER))

# Target file name (without extension).
#
# This is the name of the compiled .hex file.
TARGET ?= cross_subroutines_rsdp

# Local C source files 
#
# We don't need hammingweight, so we commenting it out
SRC += main.c ledz.c  #hammingweight.c

# External CROSS source files
#
# Define relative path to external CROSS reference C sources
CROSS_LIB_DIR = ../../libcross/variants/Reference_Implementation/lib
CROSS_WRAPPER_DIR = ../../libcross
SRC += CROSS.c pack_unpack.c csprng_hash.c fips202.c keccakf1600.c sign.c libcross.c seedtree.c merkle.c

# VPATH shows the compiler where the file directories are
VPATH += $(CROSS_LIB_DIR)
VPATH += $(CROSS_WRAPPER_DIR)

# CROSS Reference Implementation Sources
EXTRAINCDIRS += ../../libcross
EXTRAINCDIRS += ../../libcross/variants/Reference_Implementation
EXTRAINCDIRS += ../../libcross/variants/Reference_Implementation/include
EXTRAINCDIRS += ../../libcross/variants/Reference_Implementation/lib

# Target compilation flags i.e Fallback CFLAGS
ifeq ($(EXTRA_CFLAGS),)
CFLAGS += -DRSDP -DCATEGORY_1 -DSPEED
else
CFLAGS += $(EXTRA_CFLAGS)
endif
CFLAGS += -DHIGH_SPEED_UART_BAUD=230400U

# Basis-CFLAGS, which are always true
BASE_CFLAGS = -UHSE_VALUE -DHSI_VALUE=16000000U -DMCU_CLK_INT

# -----------------------------------------------------------------------------

# ifeq ($(CRYPTO_OPTIONS),)
# CRYPTO_OPTIONS = AES128C
# endif
ifeq ($(CRYPTO_TARGET),)
CRYPTO_TARGET = NONE
endif

#Add simpleserial project to build
include ../simpleserial/Makefile.simpleserial

FIRMWAREPATH = ..
include $(FIRMWAREPATH)/Makefile.inc

# memory allocation in the target. you can change this but it's best left alone
ifeq ($(PLATFORM), PINATA)
STACK_SIZE = 60K
HEAP_SIZE = 60K
LDFLAGS += -Xlinker --defsym=__stack_size__=$(STACK_SIZE)
LDFLAGS += -Xlinker --defsym=__heap_size__=$(HEAP_SIZE)
endif

LDFLAGS += -Wl,--print-memory-usage
ALL_CFLAGS += -fstack-usage # this creates %.su files with the stack allocations per function

# Optimize for execution speed instead of code size.
ALL_CFLAGS += -O3

# We don't need hammingweight, so we commenting it out
#
# specific definition of compilation of this object. This allows us to specify a different optimization flag
#$(OBJDIR)/hammingweight.o : hammingweight.c $(OBJDIR)
#	@$(ECHO_BLANK)
#	@echo Compiling:
#	@echo -en $(COMPMSG)
#	$(CC) -c $(filter-out -O$(OPT), $(ALL_CFLAGS)) $< -o $@ -O0
#	@echo -e $(DONEMSG)

# Link: create ELF output file from object files.
.SECONDARY : $(TARGET-PLAT).elf
.PRECIOUS : $(OBJ)
%.elf: $(OBJ)
	@$(ECHO_BLANK)
	@echo LINKING:
	@echo -en $(LINKMSG)
	$(LINK_COMPILER) $(ALL_CFLAGS) $^ --output $@ $(LDFLAGS)
	@echo -e $(DONEMSG)

endif