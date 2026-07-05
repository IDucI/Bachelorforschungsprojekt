# global configuration settings
ALG_PATH := ./variants/
LIBRARY_MAKEFILE = lib_Makefile
BUILD_DIR ?= build/
APP_DIR := app/
PYTHON_PACKAGE_NAME := cross

# dynamic envornment inquiry. get python version as well as the linux kernel version and pc hostname
# we use this because all of our lab workstations share their home directory and are using different linux version.
# this way they won't interfere with eachother.
ENV ?= /usr/bin/env
PYTHON ?= $(ENV) python3

KVER = $(shell uname -r)
KMAJ = $(shell echo $(KVER) | sed -e 's/^\([0-9][0-9]*\)\.[0-9][0-9]*\.[0-9][0-9]*.*/\1/')
KMIN = $(shell echo $(KVER) | sed -e 's/^[0-9][0-9]*\.\([0-9][0-9]*\)\.[0-9][0-9]*.*/\1/')
KREV = $(shell echo $(KVER) | sed -e 's/^[0-9][0-9]*\.[0-9][0-9]*\.\([0-9][0-9]*\).*/\1/')
PLATFORM ?= $(KMAJ).$(KMIN).$(KREV)

HOSTNAME := $(shell hostname -s)

# use the default compilation programs, you could override these from the terminal
SHELL ?=/usr/bin/bash
CC ?=/usr/bin/gcc
CXX ?=/usr/bin/g++

# compilations flags, not much going on here
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
#don't add -mno-sse4.1 because of valgrind illegal instruction error, valgrind version 3.18.1
	CPPFLAGS := $(filter-out -O3,$(CPPFLAGS))
endif
LDFLAGS=-lcrypto

# create a list of all the names of the variants in $(ALG_PATH)(Original Kyber)
# LIBNAMES_PATHS := $(dir $(wildcard $(ALG_PATH)*/))
# LIBNAMES := $(LIBNAMES_PATHS:$(ALG_PATH)%/=%)
# LIBNAMES := $(filter-out $(EXCLLIBS), $(LIBNAMES))

# hardcoded for testing 
LIBNAMES := cross_r_sdp_1_fast

# fancy colorful terminal printing
RED := \033[0;31m
GREEN := \033[1;32m
CYAN := \033[0;36m
NO_COLOR := \033[0m

# all variants that we want to compile. the top option in a makefile will be chosen when calling make without specifying anything else
all: $(LIBNAMES)

# directories to put the installation output in
HOME := ${HOME}/
LOCAL_LIB := $(HOME).local/lib/
LOCAL_INCLUDE := $(HOME).local/include/

# calling make with VERBOSE= will make the output verbose when it is using pip
ifneq ($(VERBOSE),)
	VERBOSE := 
else
	VERBOSE := -q
endif
EDITABLE := -e

ALG_DIR = $(ALG_PATH)$f/

# the below variables are made availabe to the makefiles called from inside this one
DEBUG = -g
# export ALG_VERSION via CMDLINE
export ALG_PATH
export DEBUG
export PLATFORM
export CPPFLAGS
export CXXFLAGS

# run clang format and autopep on your sourcecode. Please do this, it makes life so much easier
.PHONY: format
format:
	clang-format -i libcross.c libcross.h $(wildcard variants/*/function_linkage.c)
	autopep8 -i $(wildcard cross/*.py)

# configure the installation before doing make install
# this fits the normal linux install pattern of:
# make config
# make install
.PHONY: config
config:
	$(MAKE) -f $(LIBRARY_MAKEFILE) $@

# define these four commands. they do what they say.
.PHONY:  install uninstall installed
install: $(LIBNAMES) |$(LOCAL_INCLUDE)
	$(foreach f,$^, $(MAKE) -f $(LIBRARY_MAKEFILE) $@ ALG_VERSION=$f;)
	@printf 'installing for $(CYAN) %b %b$(NO_COLOR)\n' $$($(PYTHON) --version); $(PYTHON) -m pip install $(VERBOSE) $(EDITABLE) .;

	cp libcross.h $(LOCAL_INCLUDE)

# local linking magic
$(LOCAL_INCLUDE):
	mkdir -p $@
	-sudo ldconfig

uninstall:
	$(foreach f, $(LIBNAMES), $(MAKE) -f $(LIBRARY_MAKEFILE) $@ ALG_VERSION=$f;)
	@printf 'uninstalling in $(CYAN) %b %b$(NO_COLOR)\n' $$($(PYTHON) --version); $(PYTHON) -m pip uninstall $(VERBOSE) -y $(PYTHON_PACKAGE_NAME);

installed:
	@$(foreach f, $(LIBNAMES), $(MAKE) -f $(LIBRARY_MAKEFILE) $@ ALG_VERSION=$f;)
	@$(PYTHON) -m pip show $(VERBOSE) $(PYTHON_PACKAGE_NAME) 2>/dev/null && printf "$(GREEN)$(PYTHON_PACKAGE_NAME) is installed for %b %b$(NO_COLOR)\n" $$($(PYTHON) --version) || printf "$(RED)$(PYTHON_PACKAGE_NAME) is not installed for %b %b$(NO_COLOR)\n" $$($(PYTHON) --version)

# compile all variants that were found. compilation is devolved to the makefile in LIBRARY_MAKEFILE
$(LIBNAMES): libcross.c libcross.h
	$(MAKE) -f $(LIBRARY_MAKEFILE) ALG_VERSION=$@

.PHONY: clean
clean:
	-rm -f $(BUILD_DIR)bin/*
	-rm -f $(BUILD_DIR)lib/*
	-rm -f $(APP_DIR)*.o
	$(foreach f,$(LIBNAMES), rm -f pythonKemTest_$f clean;)
	$(foreach f,$(LIBNAMES), $(MAKE) -f $(LIBRARY_MAKEFILE) ALG_VERSION=$f clean;)
 
