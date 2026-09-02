ALGORITHMS    := rsdp rsdpg
CATEGORIES    := 1 3 5 
OPTIMIZATIONS := fast balanced small

VARIANTS := $(foreach a,$(ALGORITHMS),\
			$(foreach c,$(CATEGORIES),\
			$(foreach o,$(OPTIMIZATIONS),\
			cross_$(a)_$(c)_$(o))))

all: $(VARIANTS)
$(VARIANTS):
	$(MAKE) -f variant.mk ALG_VERSION=$@ run 

BUILD_DIR = build/

clean:
	rm -rf $(BUILD_DIR)
	