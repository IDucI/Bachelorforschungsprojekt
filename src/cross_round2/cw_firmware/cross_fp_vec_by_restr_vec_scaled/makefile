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

ifeq ($(HIGH_SPEED_BAUD),1)
CFLAGS += -DHIGH_SPEED_UART_BAUD=921600U
endif

SS_VER::=SS_VER_2_1
# $(error, VAR is $(SS_VER))

# Target file name (without extension).
# This is the name of the compiled .hex file.
TARGET = cross_fp_vec_by_restr_vec_scaled

# List C source files here.
# Header files (.h) are automatically pulled in.
SRC += main.c ledz.c
CFLAGS += -I../../libcross/variants/Reference_Implementation/include
CFLAGS += -DRSDP -DCATEGORY_1 -DSPEED
CFLAGS += -UHSE_VALUE -DHSE_VALUE=15000000U
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
else
endif

LDFLAGS += -Wl,--print-memory-usage
ALL_CFLAGS += -fstack-usage # this creates %.su files with the stack allocations per function



# specific definition of compilation of this object. This allows us to specify a different optimization flag
