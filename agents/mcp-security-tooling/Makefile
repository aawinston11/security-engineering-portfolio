.PHONY: help setup siem-up siem-down run demo test lint clean

UV ?= uv
SIEM_PORT ?= 8765
SIEM_URL ?= http://localhost:$(SIEM_PORT)

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

setup:  ## Install deps (uv sync --extra dev)
	$(UV) sync --extra dev

siem-up:  ## Bring up the synthetic SIEM mock at $(SIEM_URL)
	docker compose up -d --build siem-mock
	@echo "Waiting for SIEM mock to come up at $(SIEM_URL)..."
	@for i in $$(seq 1 40); do \
		curl -sf $(SIEM_URL)/health > /dev/null && echo "  ready" && exit 0; \
		sleep 0.25; \
	done; \
	echo "  TIMEOUT" && docker compose logs siem-mock && exit 1

siem-down:  ## Stop the SIEM mock
	docker compose down

run: siem-up  ## Print how to launch the MCP server interactively
	@echo
	@echo "SIEM mock running at $(SIEM_URL)."
	@echo "Start the MCP server interactively with:"
	@echo "  $(UV) run mcp dev src/mcp_security_tooling/server.py"
	@echo
	@echo "Or run the demo client (spawns the server, calls a tool, prints the trace):"
	@echo "  make demo"

demo: siem-up  ## Spawn the MCP server, exercise all 5 tools, print results
	$(UV) run python -m mcp_security_tooling.demo

test: siem-up  ## Run integration tests (needs SIEM mock up)
	$(UV) run pytest -v

lint:  ## ruff check src tests
	$(UV) run ruff check src tests

clean: siem-down  ## Stop SIEM, remove venv, caches, audit logs
	rm -rf .venv .pytest_cache .ruff_cache audit test-audit.jsonl
