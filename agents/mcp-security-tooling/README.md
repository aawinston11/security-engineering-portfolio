# MCP Security Tooling Server

A Model Context Protocol server that exposes a synthetic SIEM/EDR API to LLM agents — auth-scoped tools, deterministic responses for evals, and a tamper-evident audit trail.

**Status: WIP.** Skeleton; no working server yet.

---

## Problem

Letting an LLM agent take action against a SIEM or EDR is mostly a tooling problem. Agents need typed, auth-scoped tools with predictable shapes, and the security team needs to know exactly what the agent did and why. Most "AI for security" demos hand-roll one-off function-calling prompts that don't compose, don't audit, and don't move between models. MCP solves the contract; this project shows what a SecOps-shaped MCP surface looks like.

## What I built

- An MCP server (Python, stdio + SSE transports) exposing tools: `search_events`, `get_alert`, `enrich_indicator`, `list_hosts`, `quarantine_host` (no-op, audit-logged).
- A synthetic SIEM backing service (Docker) seeded from a labeled event corpus — designed to be deterministic so eval results are reproducible.
- Per-tool auth scopes (`read:events`, `read:alerts`, `enrich:indicators`, `act:contain`) and an append-only HMAC-chained audit log of every tool invocation, arguments hash, and result hash.
- An MCP client demo: `mcp` CLI or Claude Desktop connects, lists tools, runs a sample triage query end-to-end.

## How it works

- **Transport:** MCP over stdio for local agents, SSE for networked clients.
- **Backing service:** FastAPI app reading from `data/events.jsonl`. Synthetic but realistic field shapes (host, user, process, indicator, ATT&CK technique).
- **Auth model:** API-key scopes. Containment-class tools require `act:` and produce an audit entry signed with an HMAC chained to the previous entry — tamper-evident, replayable.
- **Determinism:** queries stable by `(query, seed)`; same input always returns same result so downstream eval scores don't drift.
- **No real telemetry:** the backing service never accepts external data. The corpus ships with the repo.

## Run it

```bash
make setup
make run        # starts SIEM mock + MCP server
make demo       # MCP client connects, runs a sample triage trace
make test
```

Prerequisites: Python 3.11+, `uv`, Docker.

## Interview-ready

_Filled in once Status reaches Stable. Will document: risk reduced, failure modes, detection, rollback, scale._

## References

- Model Context Protocol — https://modelcontextprotocol.io
- MITRE ATT&CK — https://attack.mitre.org
- NIST 800-53 — AU-2 (audit events), AU-9 (protection of audit information)
