.PHONY: setup siem-up siem-down run demo test lint clean

UV ?= uv
SIEM_PORT ?= 8765
SIEM_URL ?= http://localhost:$(SIEM_PORT)

setup:
	$(UV) sync --extra dev

siem-up:
	docker compose up -d --build siem-mock
	@echo "Waiting for SIEM mock to come up at $(SIEM_URL)..."
	@for i in $$(seq 1 40); do \
		curl -sf $(SIEM_URL)/health > /dev/null && echo "  ready" && exit 0; \
		sleep 0.25; \
	done; \
	echo "  TIMEOUT" && docker compose logs siem-mock && exit 1

siem-down:
	docker compose down

run: siem-up
	@echo
	@echo "SIEM mock running at $(SIEM_URL)."
	@echo "Start the MCP server interactively with:"
	@echo "  $(UV) run mcp dev src/mcp_security_tooling/server.py"
	@echo
	@echo "Or run the demo client (spawns the server, calls a tool, prints the trace):"
	@echo "  make demo"

demo: siem-up
	$(UV) run python -m mcp_security_tooling.demo

test: siem-up
	$(UV) run pytest -v

lint:
	$(UV) run ruff check src tests

clean: siem-down
	rm -rf .venv .pytest_cache .ruff_cache audit test-audit.jsonl
