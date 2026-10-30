
# CROSS variants
ALGORITHMS := rsdp rsdpg
CATEGORIES := 1 3 5
OPTIMIZATIONS := balanced fast small

VARIANTS := $(foreach alg,$(ALGORITHMS),$(foreach cat,$(CATEGORIES),$(foreach opt,$(OPTIMIZATIONS),$(alg)_$(cat)_$(opt))))

.PHONY: all subroutines overall build folders copy stack-usage clean clean-overall clean-all

all: subroutines

# Original subroutine firmware
subroutines:
	@$(MAKE) --no-print-directory FIRMWARE_DIR=../../cross_subroutines OUT_DIR=subroutines PREFIX=cross_subroutines stack-usage

# Firmware with keygen, sign and verify
overall:
	@$(MAKE) --no-print-directory FIRMWARE_DIR=.. OUT_DIR=overall PREFIX=cross_subroutines_stack stack-usage



# Build firmware if files are missing
build:
	@set -e; \
	missing=0; \
	for variant in $(VARIANTS); do \
		elf="$(FIRMWARE_DIR)/$(PREFIX)_$$variant-PINATA.elf"; \
		obj="$(FIRMWARE_DIR)/objdir-$(PREFIX)_$$variant"; \
		if [ ! -f "$$elf" ] || [ ! -d "$$obj" ] || \
		   [ -z "$$(find "$$obj" -name '*.su' -print -quit)" ]; then \
			missing=1; \
			break; \
		fi; \
	done; \
	if [ "$$missing" -eq 1 ]; then \
		echo "Building firmware ..."; \
		$(MAKE) --no-print-directory -C "$(FIRMWARE_DIR)"; \
	else \
		echo "All 18 firmware builds already exist."; \
	fi


# Create folders
folders:
	@set -e; \
	for variant in $(VARIANTS); do \
		mkdir -p "$(OUT_DIR)/stack_analysis_$$variant"; \
	done


# Copy ELF and object directories
copy: build folders
	@set -e; \
	for variant in $(VARIANTS); do \
		src_elf="$(FIRMWARE_DIR)/$(PREFIX)_$$variant-PINATA.elf"; \
		src_obj="$(FIRMWARE_DIR)/objdir-$(PREFIX)_$$variant"; \
		dest="$(OUT_DIR)/stack_analysis_$$variant"; \
		cp "$$src_elf" "$$dest/"; \
		rm -rf "$$dest/objdir-$(PREFIX)_$$variant"; \
		cp -a "$$src_obj" "$$dest/"; \
		echo "Copied $$variant"; \
	done


# Library stack usage reconstructed from ELF assembly
# memcpy: no stack allocation = 0 B
# memset: push {r4, r5, lr} = 3 * 4 B = 12 B
# memcmp: push {r4, r5} = 2 * 4 B = 8 B
stack-usage: copy
	@set -e; \
	for variant in $(VARIANTS); do \
		su_dir="$(OUT_DIR)/stack_analysis_$$variant/objdir-$(PREFIX)_$$variant"; \
		printf 'memcpy.c:1:1:memcpy\t0\tstatic\n' > "$$su_dir/memcpy.su"; \
		printf 'memset.c:1:1:memset\t12\tstatic\n' > "$$su_dir/memset.su"; \
		printf 'memcmp.c:1:1:memcmp\t8\tstatic\n' > "$$su_dir/memcmp.su"; \
	done


# Clean subroutines
clean:
	rm -rf -- subroutines
	rm -rf -- overall
