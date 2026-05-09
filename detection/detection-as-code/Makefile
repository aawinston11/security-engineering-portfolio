.PHONY: help setup lint validate purple-team navigator convert test all clean

UV ?= uv

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk -F':.*## ' '{printf "  %-20s %s\n", $$1, $$2}'

setup:  ## Install deps (uv sync --extra dev)
	$(UV) sync --extra dev

lint:  ## Lint rules (schema, ATT&CK tags, fixture presence)
	$(UV) run python -m detection_as_code.cli lint

validate: lint  ## Lint + validate every rule maps to ATT&CK
	$(UV) run python -m detection_as_code.cli validate-attack-mappings

purple-team:  ## Replay fixtures through the Sigma evaluator
	$(UV) run python -m detection_as_code.cli purple-team

navigator:  ## Emit ATT&CK Navigator JSON layer (build/)
	$(UV) run python -m detection_as_code.cli navigator

convert:  ## Convert rules to Splunk SPL via sigma-cli
	$(UV) run python -m detection_as_code.cli convert-spl

test:  ## Run unit tests
	$(UV) run pytest -v

all: lint validate purple-team  ## Lint + validate + purple-team (CI shape)

clean:  ## Remove venv, caches, build, generated SPL
	rm -rf .venv .pytest_cache .ruff_cache build generated-spl
