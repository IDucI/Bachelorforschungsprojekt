# Hey Emacs, this is a -*- makefile -*-
#----------------------------------------------------------------------------
# LESS generator_sample firmware target
#----------------------------------------------------------------------------

ifeq ($(HIGH_SPEED_BAUD),1)
CFLAGS += -DHIGH_SPEED_UART_BAUD=921600U
endif

SS_VER::=SS_VER_2_1

TARGET = less_generator_sample

# Target-local firmware sources.
SRC += main.c less_generator_sample.c ledz.c

# Official LESS reference implementation.
#
# The first embedded implementation uses the toy parameters, so CATEGORY
# and TARGET are intentionally not defined.
LESS_REFERENCE = ../../libless/variants/Reference_Implementation

CFLAGS += -I$(LESS_REFERENCE)/include

VPATH += $(LESS_REFERENCE)/lib

# generator_sample is implemented in codes.c.
#
# It uses the SHAKE-based CSPRNG from rng.c. The standalone SHAKE
# implementation additionally requires fips202.c and keccakf1600.c.
SRC += codes.c
SRC += rng.c
SRC += fips202.c
SRC += keccakf1600.c

# Same external-clock setting as the existing LESS Pinata firmware.
CFLAGS += -UHSE_VALUE -DHSE_VALUE=15000000U

ifeq ($(CRYPTO_TARGET),)
CRYPTO_TARGET = NONE
endif

include ../simpleserial/Makefile.simpleserial

FIRMWAREPATH = ..
include $(FIRMWAREPATH)/Makefile.inc

ifeq ($(PLATFORM), PINATA)

STACK_SIZE = 60K
HEAP_SIZE = 60K

LDFLAGS += -Xlinker --defsym=__stack_size__=$(STACK_SIZE)
LDFLAGS += -Xlinker --defsym=__heap_size__=$(HEAP_SIZE)

endif

LDFLAGS += -Wl,--print-memory-usage

ALL_CFLAGS += -fstack-usage