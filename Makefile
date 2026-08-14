.PHONY: install lint test validate evidence all staleness seal

PY ?= .venv/bin/python
PDD ?= .venv/bin/pdd
BUNDLE = pdd-bundles/pdd-cli
IMPL = implementations/pdd-cli/python-stdlib
# Where the validator loop ran (CI run URL, or urn: for local runs).
VALIDATION_RESOURCE ?= urn:pdd-cli:validation:1.0.0:local

install:
	python3 -m venv .venv
	.venv/bin/pip install -e . pytest==9.0.3 hypothesis==6.165.0

## Lint every protocol bundle with the hardened linter
lint:
	$(PDD) workflow lint

## Candidate suite under a scrubbed environment: candidate code under pytest
## must NEVER see PDD_EVIDENCE_KEY or other caller secrets, and gets a fresh
## temp HOME so it cannot read the invoking user's private files.
test:
	env -i PATH="$$PATH" HOME="$$(mktemp -d)" LANG="C.UTF-8" PBT_RUNS=200 \
		$(PY) -m pytest $(IMPL)/tests -q

## Full three-layer Validator Loop (S/B/O) with the docker sandbox
validate:
	$(PDD) workflow validate $(BUNDLE) --impl $(IMPL) --sandbox --pbt-runs 200

## Signed evidence chain + ledger verify + staleness gate (needs PDD_EVIDENCE_KEY)
evidence:
	$(PDD) workflow evidence build $(BUNDLE) --impl $(IMPL) \
		--validation-resource $(VALIDATION_RESOURCE)
	$(PDD) workflow evidence verify $(BUNDLE)
	$(PDD) workflow staleness $(BUNDLE)

## Everything a commit must pass
all: lint test validate evidence

## Seal a bundle (lint must pass first)
seal:
	$(PDD) workflow seal $(BUNDLE)
