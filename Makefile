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

