VARIANTS := \
	less_cat1_192 \
	less_cat1_68 \
	less_cat1_45 \
	less_cat3_220 \
	less_cat3_102 \
	less_cat5_345 \
	less_cat5_137

all: $(VARIANTS)

$(VARIANTS):
	$(MAKE) -f variant.mk ALG_VERSION=$@ run

BUILD_DIR := build/

clean:
	rm -rf $(BUILD_DIR)
