CC = gcc
.DEFAULT_GOAL := all

# Paths
LIBCROSS = ../../../../libcross
REF_IMPL = $(LIBCROSS)/variants/Reference_Implementation

# Compiler flags
CFLAGS = -Wall -Wextra -g -O3 \
		 -Wno-unused-function \
         -ffunction-sections -fdata-sections \
         -I$(LIBCROSS) \
         -I$(REF_IMPL)/include \
         -I$(REF_IMPL)/lib \
         -I$(REF_IMPL)

LDFLAGS = -Wl,--gc-sections

# Reference implementation sources
SOURCES = \
    cachegrind.c \
    $(REF_IMPL)/lib/CROSS.c \
    $(REF_IMPL)/lib/pack_unpack.c \
    $(REF_IMPL)/lib/csprng_hash.c \
    $(REF_IMPL)/lib/fips202.c \
    $(REF_IMPL)/lib/keccakf1600.c \
    $(REF_IMPL)/lib/sign.c \
    $(REF_IMPL)/lib/seedtree.c \
    $(REF_IMPL)/lib/merkle.c

# ============================================================================
# Parameter configurations
# ============================================================================

VARIANTS = \
    rsdp_1_fast \
    rsdp_1_balanced \
    rsdp_1_small \
    rsdp_3_fast \
    rsdp_3_balanced \
    rsdp_3_small \
    rsdp_5_fast \
    rsdp_5_balanced \
    rsdp_5_small \
    rsdpg_1_fast \
    rsdpg_1_balanced \
    rsdpg_1_small \
    rsdpg_3_fast \
    rsdpg_3_balanced \
    rsdpg_3_small \
    rsdpg_5_fast \
    rsdpg_5_balanced \
    rsdpg_5_small

RSDPG_VARIANTS = \
    rsdpg_1_fast \
    rsdpg_1_balanced \
    rsdpg_1_small \
    rsdpg_3_fast \
    rsdpg_3_balanced \
    rsdpg_3_small \
    rsdpg_5_fast \
    rsdpg_5_balanced \
    rsdpg_5_small

# ============================================================================
# Benchmark groups
# ============================================================================

# Individual subroutines common to RSDP and RSDPG
COMMON_BENCHMARKS = \
    convert_restr_vec_to_fp \
    restr_vec_by_fp_matrix \
    fp_vec_by_fp_vec_pointwise \
    fp_vec_by_fp_matrix \
    fz_vec_sub_n \
    expand_sk \
    fz_dz_norm_n \
    fp_vec_by_restr_vec_scaled \
    expand_digest_to_fixed_weight \
    pack_fp_syn \
    pack_fz_vec \
    expand_pk

# Individual subroutines specific to RSDPG
RSDPG_BENCHMARKS = \
    fz_inf_w_by_fz_matrix \
    fz_vec_sub_m \
    fz_dz_norm_m

# Complete CROSS operations
OVERALL_BENCHMARKS = \
    CROSS_keygen \
    CROSS_sign \
    CROSS_verify

# ============================================================================
# Benchmark selection
# ============================================================================

BENCH ?= convert_restr_vec_to_fp

BENCH_DEFINE = \
    -DBENCH_$(shell echo $(BENCH) | tr '[:lower:]' '[:upper:]')

TARGETS = \
    $(foreach v,$(VARIANTS),cachegrind_$(BENCH)_$(v))

RSDPG_TARGETS = \
    $(foreach v,$(RSDPG_VARIANTS),cachegrind_$(BENCH)_$(v))


# ============================================================================
# Build rules
# ============================================================================

define BUILD_template

cachegrind_$(BENCH)_$(1): $(SOURCES)
	$$(CC) $$(CFLAGS) $$(BENCH_DEFINE) \
		$(if $(findstring rsdpg,$(1)),-DRSDPG,-DRSDP) \
		$(if $(findstring _1_,$(1)),-DCATEGORY_1,) \
		$(if $(findstring _3_,$(1)),-DCATEGORY_3,) \
		$(if $(findstring _5_,$(1)),-DCATEGORY_5,) \
		$(if $(findstring _fast,$(1)),-DSPEED,) \
		$(if $(findstring _balanced,$(1)),-DBALANCED,) \
		$(if $(findstring _small,$(1)),-DSIG_SIZE,) \
		$$(SOURCES) $$(LDFLAGS) -o $$@

endef

$(foreach v,$(VARIANTS),$(eval $(call BUILD_template,$(v))))


# ============================================================================
# Run targets
# ============================================================================

.PHONY: all run run-overall run-common run-common-one \
        run-rsdpg run-rsdpg-one run-all clean


# Run the selected benchmark
run:
ifeq ($(filter $(BENCH),$(RSDPG_BENCHMARKS)),)
	@$(MAKE) run-common-one
else
	@$(MAKE) run-rsdpg-one
endif


# Run complete CROSS operations for all 18 variants
run-overall:
	@for bench in $(OVERALL_BENCHMARKS); do \
		echo ""; \
		echo "============================================================"; \
		echo "OVERALL ROUTINE: $$bench"; \
		echo "============================================================"; \
		$(MAKE) BENCH=$$bench run-common-one; \
	done


# Run all common subroutines
run-common:
	@for bench in $(COMMON_BENCHMARKS); do \
		echo ""; \
		echo "============================================================"; \
		echo "BENCHMARK: $$bench"; \
		echo "============================================================"; \
		$(MAKE) BENCH=$$bench run-common-one; \
	done


# Run one common benchmark for all 18 variants
run-common-one: $(TARGETS)
	@for target in $(TARGETS); do \
		echo ""; \
		echo "----------------------------------------"; \
		echo "Running $$target"; \
		echo "----------------------------------------"; \
		valgrind --tool=cachegrind \
		         --cache-sim=yes \
		         --branch-sim=yes \
		         ./$$target; \
	done


# Run all RSDPG-specific subroutines
run-rsdpg:
	@for bench in $(RSDPG_BENCHMARKS); do \
		echo ""; \
		echo "============================================================"; \
		echo "RSDPG BENCHMARK: $$bench"; \
		echo "============================================================"; \
		$(MAKE) BENCH=$$bench run-rsdpg-one; \
	done


# Run one RSDPG-specific benchmark for all 9 variants
run-rsdpg-one: $(RSDPG_TARGETS)
	@for target in $(RSDPG_TARGETS); do \
		echo ""; \
		echo "----------------------------------------"; \
		echo "Running $$target"; \
		echo "----------------------------------------"; \
		valgrind --tool=cachegrind \
		         --cache-sim=yes \
		         --branch-sim=yes \
		         ./$$target; \
	done


# Overall routines:       3 × 18 = 54
# Common subroutines:    12 × 18 = 216
# RSDPG subroutines:      3 ×  9 = 27
# Total: 297 measurements
run-all:
	@echo ""
	@echo "============================================================"
	@echo "          CROSS CACHEGRIND EVALUATION"
	@echo "============================================================"
	@echo ""
	@echo "Overall routines:       3 × 18 = 54"
	@echo "Common subroutines:    12 × 18 = 216"
	@echo "RSDPG subroutines:      3 ×  9 = 27"
	@echo "Total measurements: 297"
	@echo ""

	@$(MAKE) run-overall
	@$(MAKE) run-common
	@$(MAKE) run-rsdpg

	@echo ""
	@echo "============================================================"
	@echo "          CACHEGRIND EVALUATION FINISHED"
	@echo "============================================================"
	@echo "Total measurements: 297"

# Default target
all: run-all

clean:
	rm -f cachegrind_*
	rm -f cachegrind.out.*