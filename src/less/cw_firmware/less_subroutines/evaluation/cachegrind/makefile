CC = gcc
.DEFAULT_GOAL := all

# Reference implementation path
REF = ../../../../libless/variants/Reference_Implementation

CFLAGS = -std=c11 -Wall -Wextra -O3 -g -Wno-unused-function -Wno-type-limits \
         -ffunction-sections -fdata-sections \
         -I$(REF)/include -I$(REF)/lib
LDFLAGS = -Wl,--gc-sections

# Reference implementation sources
COMMON_SOURCES = \
    $(REF)/lib/codes.c \
    $(REF)/lib/monomial.c \
    $(REF)/lib/rng.c \
    $(REF)/lib/fips202.c \
    $(REF)/lib/keccakf1600.c

# Parameter configurations and benchmark groups
VARIANTS = toy cat1_192 cat1_68 cat1_45 cat3_220 cat3_102 cat5_345 cat5_137

SUBROUTINES = fq_inv row_mul3 generator_sample monomial_sample_prikey generator_monomial_mul

OVERALL_BENCHMARKS = LESS_keygen LESS_sign LESS_verify

OVERALL_SOURCES = \
    $(REF)/lib/LESS.c \
    $(REF)/lib/canonical.c \
    $(REF)/lib/seedtree.c \
    $(REF)/lib/sort.c \
    $(REF)/lib/transpose.c \
    $(REF)/lib/utils.c

BENCH ?= fq_inv
VARIANT ?= toy

ifneq ($(filter $(BENCH),$(OVERALL_BENCHMARKS)),)
SOURCES = $(COMMON_SOURCES) $(OVERALL_SOURCES)
else
SOURCES = $(COMMON_SOURCES)
endif

PARAM_toy = -DBENCH_TOY
PARAM_cat1_192 = -DCATEGORY=252 -DTARGET=192
PARAM_cat1_68  = -DCATEGORY=252 -DTARGET=68
PARAM_cat1_45  = -DCATEGORY=252 -DTARGET=45
PARAM_cat3_220 = -DCATEGORY=400 -DTARGET=220
PARAM_cat3_102 = -DCATEGORY=400 -DTARGET=102
PARAM_cat5_345 = -DCATEGORY=548 -DTARGET=345
PARAM_cat5_137 = -DCATEGORY=548 -DTARGET=137

# Benchmark selection and build targets
BENCH_DEFINE = -DBENCH_$(shell echo $(BENCH) | tr '[:lower:]' '[:upper:]')
BENCH_VARIANTS = $(if $(filter $(BENCH),$(OVERALL_BENCHMARKS)),$(filter-out toy,$(VARIANTS)),$(VARIANTS))
TARGETS = $(foreach variant,$(BENCH_VARIANTS),cachegrind_$(BENCH)_$(variant))

# Build rules
define BUILD_template
cachegrind_$(BENCH)_$(1): cachegrind.c $(SOURCES)
	$$(CC) $$(CFLAGS) $$(BENCH_DEFINE) $$(PARAM_$(1)) $$^ $$(LDFLAGS) -o $$@
endef

$(foreach variant,$(BENCH_VARIANTS),$(eval $(call BUILD_template,$(variant))))

# Build and execution targets
.PHONY: all build build-many build-all run run-subroutines run-overall run-all clean

build: cachegrind_$(BENCH)_$(VARIANT)

build-many: $(TARGETS)

build-all:
	@set -e; for bench in $(SUBROUTINES) $(OVERALL_BENCHMARKS); do \
		$(MAKE) --no-print-directory BENCH=$$bench build-many; \
	done

run: $(TARGETS)
	@set -e; for target in $(TARGETS); do \
		echo "Running $$target"; \
		valgrind --tool=cachegrind --cache-sim=yes --branch-sim=yes ./$$target; \
	done

run-subroutines:
	@set -e; for bench in $(SUBROUTINES); do \
		$(MAKE) --no-print-directory BENCH=$$bench run; \
	done

run-overall:
	@set -e; for bench in $(OVERALL_BENCHMARKS); do \
		$(MAKE) --no-print-directory BENCH=$$bench run; \
	done

run-all: run-subroutines run-overall

all: run-all

clean:
	rm -rf build
	rm -f $(foreach bench,$(SUBROUTINES) $(OVERALL_BENCHMARKS),$(foreach variant,$(VARIANTS),cachegrind_$(bench)_$(variant))) cachegrind.out.*