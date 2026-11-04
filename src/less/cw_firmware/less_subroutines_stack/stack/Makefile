VARIANTS := toy cat1_192 cat1_68 cat1_45 cat3_220 cat3_102 cat5_345 cat5_137
OVERALL_VARIANTS := cat1_192 cat1_68 cat1_45 cat3_220 cat3_102 cat5_345 cat5_137

.PHONY: all subroutines overall build folders copy stack-usage memory clean

all: subroutines

subroutines:
	@$(MAKE) --no-print-directory FIRMWARE_DIR=../../less_subroutines OUT_DIR=subroutines PREFIX=less_subroutines stack-usage

overall:
	@$(MAKE) --no-print-directory FIRMWARE_DIR=.. OUT_DIR=overall PREFIX=less_subroutines_stack VARIANTS="$(OVERALL_VARIANTS)" stack-usage

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
		echo "Building LESS firmware ..."; \
		$(MAKE) --no-print-directory -C "$(FIRMWARE_DIR)" PLATFORM=PINATA MCU_CLK=INT; \
	else \
		echo "All firmware builds already exist."; \
	fi

folders:
	@set -e; \
	for variant in $(VARIANTS); do \
		mkdir -p "$(OUT_DIR)/stack_analysis_$$variant"; \
	done

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

stack-usage: copy
	@set -e; \
	for variant in $(VARIANTS); do \
		su_dir="$(OUT_DIR)/stack_analysis_$$variant/objdir-$(PREFIX)_$$variant"; \
		printf 'memcpy.c:1:1:memcpy\t0\tstatic\n' > "$$su_dir/memcpy.su"; \
		printf 'memset.c:1:1:memset\t12\tstatic\n' > "$$su_dir/memset.su"; \
		if [ "$(OUT_DIR)" = "overall" ]; then \
			printf '__popcountsi2.c:1:1:__popcountsi2\t0\tstatic\n' > "$$su_dir/__popcountsi2.su"; \
		fi; \
	done

memory:
	python3 less_memory.py

clean:
	rm -rf -- subroutines overall