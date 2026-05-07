# MCP Security Tooling Server

A Model Context Protocol server that exposes a synthetic SIEM/EDR API to LLM agents — auth-scoped tools, deterministic responses for evals, and a tamper-evident audit trail.

**Status: WIP — early scaffold.** SIEM mock + MCP server with one working tool (`search_events`). Audit log and test suite in place. More tools, SSE transport, and full scope/auth wiring in flight.

---

## Problem

Letting an LLM agent take action against a SIEM or EDR is mostly a tooling problem. Agents need typed, auth-scoped tools with predictable shapes, and the security team needs to know exactly what the agent did and why. Most "AI for security" demos hand-roll one-off function-calling prompts that don't compose, don't audit, and don't move between models. MCP solves the contract; this project shows what a SecOps-shaped MCP surface looks like.

## What's shipped (today)

- **Synthetic SIEM mock** (FastAPI, Dockerized). Loads ~20 labeled events from `data/events.jsonl` covering encoded PowerShell, brute force, credential dumping, lateral movement, plus benign noise. API-key auth enforced. Deterministic key=value query language so eval results are reproducible.
- **MCP server** (FastMCP, stdio transport) with one working tool, `search_events`, that calls the SIEM mock and audits every invocation.
- **HMAC-chained audit log** — append-only, tamper-evident. Each entry signs `(prev_signature || payload)`, so single-line edits break verification.
- **Demo client** that spawns the server as a subprocess, lists tools, runs three search queries, prints the trace.
- **Tests** covering SIEM auth, query filtering, determinism, and audit-log integrity (including tamper detection and wrong-key detection).

## What's planned

- Additional tools: `get_alert`, `enrich_indicator`, `list_hosts`, `quarantine_host` (no-op, audit-logged, requires `act:contain` scope).
- Per-tool scope enforcement (`read:events`, `read:alerts`, `enrich:indicators`, `act:contain`).
- SSE transport for networked agents (stdio is fine for local Claude Desktop / inspector use).
- Larger event corpus and a `corpus.py` generator.

## How it works

- **Transport**: MCP over stdio. The MCP client (Claude Desktop, the `mcp dev` inspector, or our `demo.py`) launches the server as a subprocess and speaks the protocol over its stdin/stdout.
- **Backing service**: FastAPI app reading from `data/events.jsonl`. Runs in Docker (see `docker-compose.yml`). Listens on `localhost:8765`. Health endpoint: `GET /health`. Search endpoint: `GET /events/search?query=...&limit=N` with `X-API-Key` header.
- **Auth**: API key. The dev key (`dev-readonly-key`) is checked into the compose env; production deployments would use a secret manager.
- **Determinism**: queries return the same response for the same inputs. The corpus is committed; nothing about results depends on time, randomness, or external services.
- **Audit**: every tool invocation appends an entry to `audit/audit.jsonl` containing the timestamp, tool name, SHA-256 of the args, SHA-256 of the result summary, and an HMAC-chained signature. `AuditLog.verify()` returns False on any tamper.

## Run it

```bash
make setup          # uv sync (Python 3.11+ required)
make siem-up        # docker compose: SIEM mock at http://localhost:8765
make demo           # spawn server, list tools, call search_events three ways
make test           # pytest: SIEM auth, query, determinism, audit chain
make run            # prints the command to start the MCP server interactively
```

To use the server from Claude Desktop, add the following to your `claude_desktop_config.json` (path varies by OS):

```json
{
  "mcpServers": {
    "security-tooling": {
      "command": "uv",
      "args": ["--directory", "/path/to/agents/mcp-security-tooling", "run", "python", "-m", "mcp_security_tooling.server"],
      "env": {
        "SIEM_BASE_URL": "http://localhost:8765",
        "SIEM_API_KEY": "dev-readonly-key"
      }
    }
  }
}
```

Prerequisites: Python 3.11+, [`uv`](https://docs.astral.sh/uv/), Docker.

## Layout

```
agents/mcp-security-tooling/
├── pyproject.toml             # uv-managed
├── Makefile
├── docker-compose.yml         # SIEM mock service
├── Dockerfile.siem
├── data/events.jsonl          # synthetic event corpus (~20 events)
├── src/
│   ├── siem_mock/app.py       # FastAPI: /health, /events/search
│   └── mcp_security_tooling/
│       ├── server.py          # FastMCP server + tool registration
│       ├── audit.py           # HMAC-chained audit log
│       └── demo.py            # client demo
└── tests/test_e2e.py          # SIEM HTTP + audit chain
```

## Interview-ready

_Filled in once Status reaches Stable. Will document: risk reduced, failure modes, detection, rollback, scale._

## References

- Model Context Protocol — https://modelcontextprotocol.io
- MCP Python SDK / FastMCP — https://github.com/modelcontextprotocol/python-sdk
- MITRE ATT&CK — https://attack.mitre.org
- NIST SP 800-53 — AU-2 (audit events), AU-9 (protection of audit information)
