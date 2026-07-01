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
TARGET = simpleserial-databuffer

# List C source files here.
# Header files (.h) are automatically pulled in.
SRC += main.c hammingweight.c ledz.c

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
$(OBJDIR)/hammingweight.o : hammingweight.c $(OBJDIR)
	@$(ECHO_BLANK)
	@echo Compiling:
	@echo -en $(COMPMSG)
	$(CC) -c $(filter-out -O$(OPT), $(ALL_CFLAGS)) $< -o $@ -O0
	@echo -e $(DONEMSG)

Link: create ELF output file from object files.
.SECONDARY : $(TARGET-PLAT).elf
.PRECIOUS : $(OBJ)
%.elf: $(OBJ)
	@$(ECHO_BLANK)
	@echo LINKING:
	@echo -en $(LINKMSG)
	$(LINK_COMPILER) $(ALL_CFLAGS) $^ --output $@ $(LDFLAGS)
	@echo -e $(DONEMSG)