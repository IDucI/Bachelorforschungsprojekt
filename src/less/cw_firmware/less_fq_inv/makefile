# Hey Emacs, this is a -*- makefile -*-
#----------------------------------------------------------------------------
# LESS fq_inv firmware target
#----------------------------------------------------------------------------

ifeq ($(HIGH_SPEED_BAUD),1)
CFLAGS += -DHIGH_SPEED_UART_BAUD=921600U
endif

SS_VER::=SS_VER_2_1

TARGET = less_fq_inv

# Target-local firmware sources.
SRC += main.c less_fq_inv.c ledz.c

# Official LESS reference implementation.
# fq_inv is defined directly inside fq_arith.h, so no additional
# LESS .c source file is necessary for this target.
LESS_REFERENCE = ../../libless/variants/Reference_Implementation
CFLAGS += -I$(LESS_REFERENCE)/include

# Same external-clock setting as generator_monomial_mul.
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