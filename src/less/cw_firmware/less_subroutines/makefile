SS_VER = SS_VER_2_1

LESS_CATEGORY ?= toy

TARGET = less_subroutines_$(LESS_CATEGORY)


ifeq ($(LESS_CATEGORY),toy)

else ifeq ($(LESS_CATEGORY),cat1_192)

CFLAGS += -DCATEGORY=252 -DTARGET=192

else ifeq ($(LESS_CATEGORY),cat1_68)

CFLAGS += -DCATEGORY=252 -DTARGET=68

else ifeq ($(LESS_CATEGORY),cat1_45)

CFLAGS += -DCATEGORY=252 -DTARGET=45

else ifeq ($(LESS_CATEGORY),cat3_220)

CFLAGS += -DCATEGORY=400 -DTARGET=220

else ifeq ($(LESS_CATEGORY),cat3_102)

CFLAGS += -DCATEGORY=400 -DTARGET=102

else ifeq ($(LESS_CATEGORY),cat5_345)

CFLAGS += -DCATEGORY=548 -DTARGET=345

else ifeq ($(LESS_CATEGORY),cat5_137)

CFLAGS += -DCATEGORY=548 -DTARGET=137

else

$(error Unknown LESS_CATEGORY '$(LESS_CATEGORY)'; use toy, cat1_192, cat1_68, cat1_45, cat3_220, cat3_102, cat5_345 or cat5_137)

endif


SRC += main.c
SRC += ledz.c


LESS_REFERENCE = ../../libless/variants/Reference_Implementation

CFLAGS += -I$(LESS_REFERENCE)/include

VPATH += $(LESS_REFERENCE)/lib


SRC += codes.c
SRC += monomial.c
SRC += rng.c
SRC += fips202.c
SRC += keccakf1600.c


CFLAGS += -UHSE_VALUE
CFLAGS += -DHSE_VALUE=15000000U


ifeq ($(CRYPTO_TARGET),)
CRYPTO_TARGET = NONE
endif


include ../simpleserial/Makefile.simpleserial


FIRMWAREPATH = ..

include $(FIRMWAREPATH)/Makefile.inc


ifeq ($(PLATFORM), PINATA)

STACK_SIZE = 16K
HEAP_SIZE = 1K

LDFLAGS += -Xlinker --defsym=__stack_size__=$(STACK_SIZE)
LDFLAGS += -Xlinker --defsym=__heap_size__=$(HEAP_SIZE)

endif


LDFLAGS += -Wl,--print-memory-usage

ALL_CFLAGS += -fstack-usage