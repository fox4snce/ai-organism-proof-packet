PY?=python
PP?=bin/pp
DEMO_FILES=$(shell ls demos/*.json)

.PHONY: demo verify bench clean

demo:
	@$(PP) run $(DEMO_FILES) --out runs/

verify:
	@$(PP) verify runs/ golden/

bench:
	@$(PP) bench --concurrency $(N)

clean:
	rm -rf runs/*

.PHONY: ci
ci:
	@$(PP) run demos/*.json --out runs/
	@$(PP) verify runs/ golden/
	@$(PP) bench --concurrency 32
	@$(PP) bench --concurrency 128

.PHONY: goldens
goldens:
	@$(PP) run demos/*.json --out runs/
	@$(PP) verify runs/ golden/

