ALGORITHMS    := rsdp rsdpg
CATEGORIES    := 1 3 5 
OPTIMIZATIONS := fast balanced small

VARIANTS := $(foreach a,$(ALGORITHMS),\
			$(foreach c,$(CATEGORIES),\
			$(foreach o,$(OPTIMIZATIONS),\
			cross_$(a)_$(c)_$(o))))

.PHONY: generate test_wrappers verify_py test $(VARIANTS) clean

generate: $(VARIANTS)
$(VARIANTS):
	$(MAKE) -f variant.mk ALG_VERSION=$@ run 

test_wrappers: generate
	PYTHONPATH=.. python3 test_cross.py

verify_py: test_wrappers
	@for variant in $(VARIANTS); do \
		$(MAKE) -f variant.mk \
		ALG_VERSION=$$variant \
		TEST_SRC=verify_py.c \
		TEST_NAME=verify_py \
		run || exit $$?; \
	done

test: verify_py
	@printf "\033[1;92m\n=============================================\n"
	@printf "              ALL TESTS PASSED\n"
	@printf "=============================================\033[0m\n"

BUILD_DIR = build/

clean:
	rm -rf $(BUILD_DIR)
	rm -rf *.json
	