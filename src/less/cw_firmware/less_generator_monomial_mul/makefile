# Hey Emacs, this is a -*- makefile -*-
#----------------------------------------------------------------------------
# LESS generator_monomial_mul firmware target, based on the supervisor's
# simpleserial-databuffer target and the current CROSS firmware structure.
#----------------------------------------------------------------------------

ifeq ($(HIGH_SPEED_BAUD),1)
CFLAGS += -DHIGH_SPEED_UART_BAUD=921600U
endif

SS_VER::=SS_VER_2_1

TARGET = less_generator_monomial_mul

# Target-local firmware sources.
SRC += main.c less_monomial_mul.c ledz.c

# Official LESS reference implementation. The first incremental firmware uses
# the toy parameters, so CATEGORY and TARGET are intentionally not defined.
LESS_REFERENCE = ../../libless/variants/Reference_Implementation
CFLAGS += -I$(LESS_REFERENCE)/include
VPATH += $(LESS_REFERENCE)/lib
SRC += codes.c

# Same external-clock setting used by the current CROSS Pinata target.
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
