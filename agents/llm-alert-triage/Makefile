.PHONY: setup siem-up siem-down run eval test lint clean

UV ?= uv
MCP_DIR ?= ../mcp-security-tooling

setup:
	$(UV) sync --extra dev

siem-up:
	$(MAKE) -C $(MCP_DIR) siem-up

siem-down:
	$(MAKE) -C $(MCP_DIR) siem-down

run: siem-up
	@if [ -z "$$ANTHROPIC_API_KEY" ]; then \
		echo "ANTHROPIC_API_KEY is not set."; exit 1; \
	fi
	$(UV) run python -m alert_triage.cli run

eval: siem-up
	@if [ -z "$$ANTHROPIC_API_KEY" ]; then \
		echo "ANTHROPIC_API_KEY is not set."; exit 1; \
	fi
	$(UV) run python -m alert_triage.cli eval

test:
	$(UV) run pytest -v

lint:
	$(UV) run ruff check src tests

clean:
	rm -rf .venv .pytest_cache .ruff_cache eval-results
