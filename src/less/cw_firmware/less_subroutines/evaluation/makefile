SHELL := /bin/bash

RESULTS_DIR := results

.PHONY: runtime host-build cachegrind memcheck clean

.DEFAULT_GOAL := host-build


runtime:
	@python3 runtime_measurement.py

host-build:
	@$(MAKE) -C cachegrind build-all

cachegrind: host-build
	@cd cachegrind && python3 collect_cachegrind.py all

memcheck: host-build
	@cd cachegrind && python3 collect_memcheck.py all

clean:
	@rm -rf $(RESULTS_DIR)