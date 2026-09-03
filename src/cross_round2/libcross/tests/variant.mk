LIB_DIR    := ../variants/$(ALG_VERSION)/lib/
LIB_OBJECTS := $(wildcard $(LIB_DIR)*.s.o)

TEST_SRC := test_cross.c

ALG_DIR := ../variants/Reference_Implementation/

SHELL?=/usr/bin/bash
CC?=/usr/bin/gcc
CXX?=/usr/bin/g++
CFLAGS += -std=c11
CPPFLAGS += -I $(ALG_DIR) -I $(ALG_DIR)include

# determine compiler flags from ALG_VERSION in the format cross_<algorithm>_<category>_<optimization> e.g. cross_rsdp_1_fast
VARIANT_PARTS := $(subst _, ,$(ALG_VERSION))

ALGORITHM    := $(word 2, $(VARIANT_PARTS))
CATEGORY     := $(word 3, $(VARIANT_PARTS))
OPTIMIZATION := $(word 4, $(VARIANT_PARTS))

BUILD_DIR := build/
OBJ_DIR   := $(BUILD_DIR)$(ALG_VERSION)/
TEST_BIN  := $(OBJ_DIR)cross_test

$(info ALG_VERSION = $(ALG_VERSION))
$(info ALG_DIR     = $(ALG_DIR))
$(info OBJ_DIR     = $(OBJ_DIR))

ALGORITHM_FLAG_rsdp  := -DRSDP
ALGORITHM_FLAG_rsdpg := -DRSDPG

CATEGORY_FLAG_1 := -DCATEGORY_1
CATEGORY_FLAG_3 := -DCATEGORY_3
CATEGORY_FLAG_5 := -DCATEGORY_5

OPTIMIZATION_FLAG_fast     := -DSPEED
OPTIMIZATION_FLAG_balanced := -DBALANCED
OPTIMIZATION_FLAG_small    := -DSIG_SIZE

VARIANT_CPPFLAGS := \
	$(ALGORITHM_FLAG_$(ALGORITHM)) \
	$(CATEGORY_FLAG_$(CATEGORY)) \
	$(OPTIMIZATION_FLAG_$(OPTIMIZATION)) \
	-DALG_VERSION='"$(ALG_VERSION)"'

CPPFLAGS += $(VARIANT_CPPFLAGS)

all: $(TEST_BIN)

$(TEST_BIN): $(TEST_SRC) $(LIB_OBJECTS) | $(OBJ_DIR)
	$(CC) $(CFLAGS) $(CPPFLAGS) $(TEST_SRC) $(LIB_OBJECTS) -o $(TEST_BIN)

run: $(TEST_BIN)
	$(TEST_BIN)

$(OBJ_DIR):
	mkdir -p $(OBJ_DIR)