PLATFORM = PINATA
MCU_CLK ?= INT

ifndef BUILD_SUB_VARIANT

.DEFAULT_GOAL := all

LESS_CATEGORIES := cat1_192 cat1_68 cat1_45 cat3_220 cat3_102 cat5_345 cat5_137

.PHONY: all clean $(LESS_CATEGORIES)

all: $(LESS_CATEGORIES)

$(LESS_CATEGORIES):
	$(MAKE) --no-print-directory -f makefile BUILD_SUB_VARIANT=1 \
		LESS_CATEGORY=$@ TARGET=less_subroutines_stack_$@ \
		OBJDIR=objdir-less_subroutines_stack_$@ PLATFORM=$(PLATFORM) MCU_CLK=$(MCU_CLK) all

clean:
	rm -rf objdir-less_subroutines_stack_*
	rm -f less_subroutines_stack_*-PINATA.hex less_subroutines_stack_*-PINATA.elf \
		less_subroutines_stack_*-PINATA.map less_subroutines_stack_*-PINATA.lss \
		less_subroutines_stack_*-PINATA.sym less_subroutines_stack_*-PINATA.bin

else

SS_VER = SS_VER_2_1

LESS_CATEGORY ?= cat1_192

TARGET = less_subroutines_stack_$(LESS_CATEGORY)

# Map each LESS variant to its reference implementation parameters.
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

# Use the selected LESS reference implementation sources for the firmware.
LESS_REFERENCE = ../../libless/variants/Reference_Implementation

CFLAGS += -I$(LESS_REFERENCE)/include

VPATH += $(LESS_REFERENCE)/lib


SRC += codes.c
SRC += monomial.c
SRC += rng.c
SRC += fips202.c
SRC += keccakf1600.c
SRC += LESS.c
SRC += canonical.c
SRC += seedtree.c
SRC += sort.c
SRC += transpose.c
SRC += utils.c


ifeq ($(CRYPTO_TARGET),)
CRYPTO_TARGET = NONE
endif


include ../simpleserial/Makefile.simpleserial


FIRMWAREPATH = ..

# Use the local HAL for static stack analysis.
override HALPATH := hal/chipwhisperer-fw-extra
override HALBASE := hal/

include $(FIRMWAREPATH)/Makefile.inc


# Configure stack and heap sizes for the Pinata firmware.
ifeq ($(PLATFORM), PINATA)

STACK_SIZE = 16K
HEAP_SIZE = 1K

LDFLAGS += -Xlinker --defsym=__stack_size__=$(STACK_SIZE)
LDFLAGS += -Xlinker --defsym=__heap_size__=$(HEAP_SIZE)

endif


LDFLAGS += -Wl,--print-memory-usage

ALL_CFLAGS += -fstack-usage

endif