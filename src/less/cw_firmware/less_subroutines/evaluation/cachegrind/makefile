CC = gcc
.DEFAULT_GOAL := all

REF = ../../../../libless/variants/Reference_Implementation

CFLAGS = -std=c11 -Wall -Wextra -O3 -g -Wno-unused-function -Wno-type-limits \
         -ffunction-sections -fdata-sections \
         -I$(REF)/include -I$(REF)/lib
LDFLAGS = -Wl,--gc-sections

COMMON_SOURCES = \
    $(REF)/lib/codes.c \
    $(REF)/lib/monomial.c \
    $(REF)/lib/rng.c \
    $(REF)/lib/fips202.c \
    $(REF)/lib/keccakf1600.c

VARIANTS = toy cat1_192 cat1_68 cat1_45 cat3_220 cat3_102 cat5_345 cat5_137

SUBROUTINES = fq_inv row_mul3 generator_sample monomial_sample_prikey generator_monomial_mul

BENCH ?= fq_inv
VARIANT ?= toy

PARAM_toy = -DBENCH_TOY
PARAM_cat1_192 = -DCATEGORY=252 -DTARGET=192
PARAM_cat1_68  = -DCATEGORY=252 -DTARGET=68
PARAM_cat1_45  = -DCATEGORY=252 -DTARGET=45
PARAM_cat3_220 = -DCATEGORY=400 -DTARGET=220
PARAM_cat3_102 = -DCATEGORY=400 -DTARGET=102
PARAM_cat5_345 = -DCATEGORY=548 -DTARGET=345
PARAM_cat5_137 = -DCATEGORY=548 -DTARGET=137

BENCH_DEFINE = -DBENCH_$(shell echo $(BENCH) | tr '[:lower:]' '[:upper:]')
BENCH_VARIANTS = $(VARIANTS)
TARGETS = $(foreach variant,$(BENCH_VARIANTS),cachegrind_$(BENCH)_$(variant))

define BUILD_template
cachegrind_$(BENCH)_$(1): cachegrind.c $(COMMON_SOURCES)
	$$(CC) $$(CFLAGS) $$(BENCH_DEFINE) $$(PARAM_$(1)) $$^ $$(LDFLAGS) -o $$@
endef

$(foreach variant,$(BENCH_VARIANTS),$(eval $(call BUILD_template,$(variant))))

.PHONY: all build build-many build-all run run-subroutines clean

build: cachegrind_$(BENCH)_$(VARIANT)

build-many: $(TARGETS)

build-all:
	@set -e; for bench in $(SUBROUTINES); do \
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

all: run-subroutines

clean:
	rm -rf build
	rm -f $(foreach bench,$(SUBROUTINES),$(foreach variant,$(VARIANTS),cachegrind_$(bench)_$(variant))) cachegrind.out.*