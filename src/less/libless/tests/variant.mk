LIB_OBJECTS := $(wildcard ../variants/$(ALG_VERSION)/*.s.o ../variants/$(ALG_VERSION)/lib/*.s.o)
TEST_SRC := test_less.c
ALG_DIR := ../variants/Reference_Implementation/

SHELL ?= /usr/bin/bash
CC ?= /usr/bin/gcc
CFLAGS += -std=c11
CPPFLAGS += -I $(ALG_DIR) -I $(ALG_DIR)include

VARIANT_PARTS := $(subst _, ,$(ALG_VERSION))
CATEGORY_NAME := $(word 2,$(VARIANT_PARTS))
TARGET := $(word 3,$(VARIANT_PARTS))

# CATEGORY values defined by the LESS reference implementation.
CATEGORY_VALUE_cat1 := 252
CATEGORY_VALUE_cat3 := 400
CATEGORY_VALUE_cat5 := 548

CPPFLAGS += \
	-DCATEGORY=$(CATEGORY_VALUE_$(CATEGORY_NAME)) \
	-DTARGET=$(TARGET) \
	-DALG_VERSION='"$(ALG_VERSION)"'

BUILD_DIR := build/
OBJ_DIR := $(BUILD_DIR)$(ALG_VERSION)/
TEST_BIN := $(OBJ_DIR)less_test

all: $(TEST_BIN)

$(TEST_BIN): $(TEST_SRC) $(LIB_OBJECTS) | $(OBJ_DIR)
	$(CC) $(CFLAGS) $(CPPFLAGS) $(TEST_SRC) $(LIB_OBJECTS) -o $(TEST_BIN)

run: $(TEST_BIN)
	$(TEST_BIN)

$(OBJ_DIR):
	mkdir -p $(OBJ_DIR)
