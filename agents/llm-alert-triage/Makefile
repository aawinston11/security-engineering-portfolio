.PHONY: setup siem-up siem-down run eval test lint clean

UV ?= uv
MCP_DIR ?= ../mcp-security-tooling

setup:
	$(UV) sync --extra dev

siem-up:
	$(MAKE) -C $(MCP_DIR) siem-up

siem-down:
	$(MAKE) -C $(MCP_DIR) siem-down

run: siem-up _check_key
	$(UV) run python -m alert_triage.cli run

eval: siem-up _check_key
	$(UV) run python -m alert_triage.cli eval

_check_key:
	@backend=$${LLM_BACKEND:-anthropic}; \
	if [ "$$backend" = "anthropic" ] && [ -z "$$ANTHROPIC_API_KEY" ]; then \
		echo "ANTHROPIC_API_KEY is not set (LLM_BACKEND=anthropic)."; exit 1; \
	elif [ "$$backend" = "openai" ] && [ -z "$$OPENAI_API_KEY" ]; then \
		echo "OPENAI_API_KEY is not set (LLM_BACKEND=openai)."; exit 1; \
	fi

test:
	$(UV) run pytest -v

lint:
	$(UV) run ruff check src tests

clean:
	rm -rf .venv .pytest_cache .ruff_cache eval-results
