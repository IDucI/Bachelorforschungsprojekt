# global configuration settings
ALG_PATH := ./variants/
LIBRARY_MAKEFILE = lib_Makefile
BUILD_DIR ?= build/
APP_DIR := app/
PYTHON_PACKAGE_NAME := less

# dynamic environment inquiry: get Python and platform information
ENV ?= /usr/bin/env
PYTHON ?= $(ENV) python3

KVER = $(shell uname -r)
KMAJ = $(shell echo $(KVER) | sed -e 's/^\([0-9][0-9]*\)\.[0-9][0-9]*\.[0-9][0-9]*.*/\1/')
KMIN = $(shell echo $(KVER) | sed -e 's/^[0-9][0-9]*\.\([0-9][0-9]*\)\.[0-9][0-9]*.*/\1/')
KREV = $(shell echo $(KVER) | sed -e 's/^[0-9][0-9]*\.[0-9][0-9]*\.\([0-9][0-9]*\).*/\1/')
PLATFORM ?= $(KMAJ).$(KMIN).$(KREV)

HOSTNAME := $(shell hostname -s)

# use the default compilation programs
SHELL ?= /usr/bin/bash
CC ?= /usr/bin/gcc
CXX ?= /usr/bin/g++

# compilation flags
CPPFLAGS += -O3 -fomit-frame-pointer -fPIC

ifeq ($(MARCH), compatible)
	CPPFLAGS += -march=core2
else
	CPPFLAGS += -march=native
endif

CPPFLAGS += -I .
CXXFLAGS += -std=c++11

ifeq ($(DEBUG), 1)
	CPPFLAGS += -g -O1 -mno-sse4.1 -fsanitize=undefined
	CPPFLAGS := $(filter-out -O3,$(CPPFLAGS))
endif

LDFLAGS :=

# LESS toy and official parameter-set variants.
LIBNAMES := \
	less_toy \
	less_cat1_192 \
	less_cat1_68 \
	less_cat1_45 \
	less_cat3_220 \
	less_cat3_102 \
	less_cat5_345 \
	less_cat5_137

# colorful terminal output
RED := \033[0;31m
GREEN := \033[1;32m
CYAN := \033[0;36m
NO_COLOR := \033[0m

# default target
all: $(LIBNAMES)

# installation directories
HOME := ${HOME}/
LOCAL_LIB := $(HOME).local/lib/
LOCAL_INCLUDE := $(HOME).local/include/

ifneq ($(VERBOSE),)
	VERBOSE :=
else
	VERBOSE := -q
endif

EDITABLE := -e

ALG_DIR = $(ALG_PATH)$f/

# variables exported to lib_Makefile

export ALG_PATH
export DEBUG
export PLATFORM
export CPPFLAGS
export CXXFLAGS

.PHONY: format
format:
	clang-format -i libless.c libless.h $(wildcard variants/*/function_linkage.c)
	autopep8 -i $(wildcard less/*.py)

.PHONY: config
config:
	$(MAKE) -f $(LIBRARY_MAKEFILE) $@

.PHONY: install uninstall installed
install: $(LIBNAMES) | $(LOCAL_INCLUDE)
	$(foreach f,$^,$(MAKE) -f $(LIBRARY_MAKEFILE) $@ ALG_VERSION=$f;)
	@printf 'installing for $(CYAN) %b %b$(NO_COLOR)\n' $$($(PYTHON) --version)
	$(PYTHON) -m pip install $(VERBOSE) $(EDITABLE) .
	cp libless.h $(LOCAL_INCLUDE)

$(LOCAL_INCLUDE):
	mkdir -p $@
	-sudo ldconfig

uninstall:
	$(foreach f,$(LIBNAMES),$(MAKE) -f $(LIBRARY_MAKEFILE) $@ ALG_VERSION=$f;)
	@printf 'uninstalling in $(CYAN) %b %b$(NO_COLOR)\n' $$($(PYTHON) --version)
	$(PYTHON) -m pip uninstall $(VERBOSE) -y $(PYTHON_PACKAGE_NAME)

installed:
	@$(foreach f,$(LIBNAMES),$(MAKE) -f $(LIBRARY_MAKEFILE) $@ ALG_VERSION=$f;)
	@$(PYTHON) -m pip show $(VERBOSE) $(PYTHON_PACKAGE_NAME) 2>/dev/null \
		&& printf "$(GREEN)$(PYTHON_PACKAGE_NAME) is installed for %b %b$(NO_COLOR)\n" $$($(PYTHON) --version) \
		|| printf "$(RED)$(PYTHON_PACKAGE_NAME) is not installed for %b %b$(NO_COLOR)\n" $$($(PYTHON) --version)

# Delegate compilation of each variant to lib_Makefile.
$(LIBNAMES): libless.c libless.h
	$(MAKE) -f $(LIBRARY_MAKEFILE) ALG_VERSION=$@

.PHONY: clean
clean:
	-rm -f $(BUILD_DIR)bin/*
	-rm -f $(BUILD_DIR)lib/*
	-rm -f $(APP_DIR)*.o
	$(foreach f,$(LIBNAMES),rm -f pythonKemTest_$f clean;)
	$(foreach f,$(LIBNAMES),$(MAKE) -f $(LIBRARY_MAKEFILE) ALG_VERSION=$f clean;)