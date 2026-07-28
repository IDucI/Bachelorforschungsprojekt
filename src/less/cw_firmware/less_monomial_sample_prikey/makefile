# Hey Emacs, this is a -*- makefile -*-
#----------------------------------------------------------------------------
# LESS monomial_sample_prikey firmware target.
#----------------------------------------------------------------------------

ifeq ($(HIGH_SPEED_BAUD),1)
CFLAGS += -DHIGH_SPEED_UART_BAUD=921600U
endif

SS_VER::=SS_VER_2_1

TARGET = less_monomial_sample_prikey

# Target-local firmware sources.
SRC += main.c less_monomial_sample_prikey.c ledz.c

# Official LESS reference implementation.
#
# CATEGORY and TARGET are intentionally not defined, so the toy
# parameter set is used.
LESS_REFERENCE = ../../libless/variants/Reference_Implementation

CFLAGS += -I$(LESS_REFERENCE)/include

VPATH += $(LESS_REFERENCE)/lib

# monomial_sample_prikey is implemented in monomial.c.
#
# It uses the SHAKE-based CSPRNG from rng.c. The standalone SHAKE
# implementation additionally requires fips202.c and keccakf1600.c.
SRC += monomial.c
SRC += rng.c
SRC += fips202.c
SRC += keccakf1600.c

# Same external clock as the other LESS Pinata firmware targets.
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