.PHONY: help setup siem-up siem-down run eval test lint clean

UV ?= uv
MCP_DIR ?= ../mcp-security-tooling

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

setup:  ## Install deps (uv sync --extra dev)
	$(UV) sync --extra dev

siem-up:  ## Bring up the synthetic SIEM mock (Docker)
	$(MAKE) -C $(MCP_DIR) siem-up

siem-down:  ## Stop the SIEM mock
	$(MAKE) -C $(MCP_DIR) siem-down

run: siem-up _check_key  ## Triage one alert (default: ALERT-001)
	$(UV) run python -m alert_triage.cli run

eval: siem-up _check_key  ## Run eval harness on 15 labeled alerts (~$0.05-0.15)
	$(UV) run python -m alert_triage.cli eval

_check_key:
	@if [ -f ../../.env ]; then set -a; . ../../.env; set +a; fi; \
	backend=$${LLM_BACKEND:-anthropic}; \
	if [ "$$backend" = "anthropic" ] && [ -z "$$ANTHROPIC_API_KEY" ]; then \
		echo "ANTHROPIC_API_KEY is not set."; \
		echo "Add it to .env at the repo root, or export it in your shell."; \
		exit 1; \
	elif [ "$$backend" = "openai" ] && [ -z "$$OPENAI_API_KEY" ]; then \
		echo "OPENAI_API_KEY is not set."; \
		echo "Add it to .env at the repo root, or export it in your shell."; \
		exit 1; \
	fi

test:  ## Run unit tests (no LLM, no Docker)
	$(UV) run pytest -v

lint:  ## ruff check src tests
	$(UV) run ruff check src tests

clean:  ## Remove venv, caches, eval-results
	rm -rf .venv .pytest_cache .ruff_cache eval-results
