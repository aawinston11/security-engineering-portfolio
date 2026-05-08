.PHONY: setup run eval test lint clean

UV ?= uv

setup:
	$(UV) sync --extra dev

run: _check_key
	$(UV) run python -m ir_copilot.cli run

eval: _check_key
	$(UV) run python -m ir_copilot.cli eval

redteam: _check_key
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

test:
	$(UV) run pytest -v

lint:
	$(UV) run ruff check src tests

clean:
	rm -rf .venv .pytest_cache .ruff_cache eval-results
