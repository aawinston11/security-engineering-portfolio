.PHONY: help setup run eval redteam test lint clean

UV ?= uv

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

setup:  ## Install deps (uv sync --extra dev)
	$(UV) sync --extra dev

run: _check_key  ## Generate IR doc for first transcript (default: INC-001)
	$(UV) run python -m ir_copilot.cli run

eval: _check_key  ## Score 5 happy-path transcripts (~$0.05-0.15)
	$(UV) run python -m ir_copilot.cli eval

redteam: _check_key  ## Run 3 prompt-injection cases; assert defenses hold
	$(UV) run python -m ir_copilot.cli redteam

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

test:  ## Run unit tests (no LLM)
	$(UV) run pytest -v

lint:  ## ruff check src tests
	$(UV) run ruff check src tests

clean:  ## Remove venv, caches, eval-results
	rm -rf .venv .pytest_cache .ruff_cache eval-results
