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

# Explicitly sets the shell to Bash so that 'echo -e' and subshells run smoothly
SHELL := /usr/bin/bash

DIRNAME := $(notdir $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST))))))

# =============================================================================
# VARIANTS BUILD LOOP (Executed when no "BUILD_SUB_VARIANT" variable exists)
# =============================================================================

ifndef BUILD_SUB_VARIANT

.DEFAULT_GOAL := hex

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

.PHONY: hex all clean $(HEXNAMES)

all: hex

hex: $(HEXNAMES)
	@echo "--------------------------------------------------------"
	@echo " All 18 firmware projects successfully generated!"
	@echo "--------------------------------------------------------"

$(HEXNAMES):
	@RAW_VAR=$$(echo $@ | cut -d'_' -f2); \
	if [ "$$RAW_VAR" = "rsdpg" ]; then VAR="RSDP_G"; else VAR="RSDP"; fi; \
	CAT=$$(echo $@ | cut -d'_' -f3); \
	OPT_RAW=$$(echo $@ | cut -d'_' -f4); \
	if [ "$$OPT_RAW" = "fast" ]; then OPT="SPEED"; elif [ "$$OPT_RAW" = "small" ]; then OPT="SIG_SIZE"; else OPT="BALANCED"; fi; \
	CLEAN_NAME=$$(echo $@ | sed 's/^cross_//'); \
	FULL_TARGET="$(DIRNAME)_$$CLEAN_NAME"; \
	echo "======================================================================"; \
	echo " Building Firmware Variant: $$FULL_TARGET"; \
	echo "======================================================================"; \
	$(MAKE) --no-print-directory \
		BUILD_SUB_VARIANT=1 \
		TARGET=$$FULL_TARGET \
		OBJDIR=objdir-$$FULL_TARGET \
		SS_VER=SS_VER_2_1 \
		MCU_CLK=$(MCU_CLK) \
		CRYPTO_TARGET=NONE \
		EXTRA_CFLAGS="-D$$VAR -DCATEGORY_$$CAT -D$$OPT" \
		build_all || exit 1

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
# This is the name of the compiled .hex file.
TARGET ?= cross_subroutines_rsdp

# Local C source files 
SRC += main.c hammingweight.c ledz.c

# External CROSS source files
CROSS_LIB_DIR = ../../libcross/variants/Reference_Implementation/lib
SRC += $(CROSS_LIB_DIR)/CROSS.c
SRC += $(CROSS_LIB_DIR)/pack_unpack.c
SRC += $(CROSS_LIB_DIR)/csprng_hash.c
SRC += $(CROSS_LIB_DIR)/fips202.c
SRC += $(CROSS_LIB_DIR)/keccakf1600.c
SRC += $(CROSS_LIB_DIR)/sign.c

# CROSS Reference Implementation Sources
EXTRAINCDIRS += ../../libcross
EXTRAINCDIRS += ../../libcross/variants/Reference_Implementation
EXTRAINCDIRS += ../../libcross/variants/Reference_Implementation/include
EXTRAINCDIRS += ../../libcross/variants/Reference_Implementation/lib

# Variante-Flags an die ChipWhisperer Extra-CFLAGS übergeben
EXTRA_CFLAGS += $(EXTRA_CFLAGS)

# Target compilation flags i.e Fallback CFLAGS
CFLAGS ?= -DRSDP -DCATEGORY_1 -DSPEED
CFLAGS += $(EXTRA_CFLAGS)
CFLAGS += -DHIGH_SPEED_UART_BAUD=230400U

# Basis-CFLAGS, which are always true
# ChipWhisperer Nano nutzt den internen 16MHz HSI-Takt des STM32
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

# specific definition of compilation of this object. This allows us to specify a different optimization flag
$(OBJDIR)/hammingweight.o : hammingweight.c $(OBJDIR)
	@$(ECHO_BLANK)
	@echo Compiling:
	@echo -en $(COMPMSG)
	$(CC) -c $(filter-out -O$(OPT), $(ALL_CFLAGS)) $< -o $@ -O0
	@echo -e $(DONEMSG)


OBJCOPY ?= arm-none-eabi-objcopy
OBJDUMP ?= arm-none-eabi-objdump
NM      ?= arm-none-eabi-nm

.PHONY: build_all

build_all: $(TARGET)-$(PLATFORM).hex \
           $(TARGET)-$(PLATFORM).bin \
           $(TARGET)-$(PLATFORM).sym \
           $(TARGET)-$(PLATFORM).eep \
           $(TARGET)-$(PLATFORM).lss

# HIER FEHLTE DIE HEX-REGEL:
$(TARGET)-$(PLATFORM).hex: $(TARGET)-$(PLATFORM).elf
	@echo "Creating HEX file: $@"
	$(OBJCOPY) -O ihex $< $@

$(TARGET)-$(PLATFORM).bin: $(TARGET)-$(PLATFORM).elf
	@echo "Creating Binary: $@"
	$(OBJCOPY) -O binary $< $@

$(TARGET)-$(PLATFORM).sym: $(TARGET)-$(PLATFORM).elf
	@echo "Creating Symbol Table: $@"
	$(NM) -n $< > $@

$(TARGET)-$(PLATFORM).eep: $(TARGET)-$(PLATFORM).elf
	@echo "Creating EEPROM file: $@"
	@-$(OBJCOPY) -j .eeprom --set-section-flags=.eeprom="alloc,load" --change-section-lma .eeprom=0 --no-change-warnings -O ihex $< $@ || exit 0

$(TARGET)-$(PLATFORM).lss: $(TARGET)-$(PLATFORM).elf
	@echo "Creating Disassembly Listing: $@"
	$(OBJDUMP) -h -S $< > $@

endif