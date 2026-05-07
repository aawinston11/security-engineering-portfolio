# LLM Alert Triage

A triage agent that consumes synthetic alerts, enriches them via the [MCP Security Tooling Server](../mcp-security-tooling/), and emits schema-validated triage decisions. Ships with an eval harness scoring accuracy, false-positive rate, schema validity, and per-call cost/latency on a labeled 15-alert dataset.

**Status: Beta.** Anthropic backend works end-to-end (`make run` and `make eval`). Ollama backend is stubbed pending the LLM lab box rebuild — see [`notes/runbooks/llm-box-rebuild.md`](../../notes/runbooks/llm-box-rebuild.md).

---

## Problem

LLM-based alert triage is easy to demo and hard to trust. The interesting questions aren't "can the model write a verdict" but "how often is it wrong, in which direction, and how do you know when to stop trusting it?" That requires labeled data, a pinned schema, and an eval harness that runs in CI — not screenshots from a single prompt.

## What's shipped

- A triage agent (Anthropic API, manual agentic loop) that ingests an alert, calls into the MCP server's `search_events` tool to enrich it, and emits a Pydantic-validated `TriageDecision` (`severity`, `verdict`, `confidence`, `reasoning`, `recommended_actions`, `mitre_techniques`).
- Output constrained server-side via `output_config.format` JSON schema, then validated client-side via Pydantic for constraints the API schema can't express (Literal enums, extra-field rejection).
- Adaptive thinking + `effort=medium`. Prompt caching on the system prompt + tool schemas (top-level `cache_control={"type": "ephemeral"}`).
- A labeled synthetic dataset of 15 alerts mapping into the MCP server's seeded event corpus, covering true positives, false positives, benign noise, and ambiguous cases requiring tool-driven enrichment.
- Eval harness (`make eval`): per-alert verdict accuracy, severity accuracy, MITRE technique IoU, schema-validation rate, false-positive rate, latency, and per-call cost. Results are pretty-printed and archived to `eval-results/eval-<timestamp>.json`.
- Hybrid LLM client: `LLM_BACKEND=anthropic` (default, Sonnet 4.6) or `LLM_BACKEND=ollama` (stubbed).
- Tests for schema validity, dataset alignment, and MCP→Anthropic tool conversion.

## How it works

```
                                                     [ MCP server ]
                                                     stdio subprocess
                                                            |
                                                            v
[ alert.json ] -> [ agent loop ] <-- tool_use <-- [ Anthropic API ] -> [ TriageDecision ]
                       |                                                  ^
                       |                                                  |
                       +------------ output_config.format -----------------+
                       +------------ adaptive thinking --------------------+
                       +------------ prompt caching -----------------------+
```

- Agent spawns the MCP server (`uv run --directory ../mcp-security-tooling python -m mcp_security_tooling.server`) over stdio at the start of each session.
- Lists tools, converts each MCP tool spec to an Anthropic tool definition, then runs the loop:
  1. `messages.create()` with the alert, tools, system prompt, `output_config.format=TRIAGE_OUTPUT_SCHEMA`, adaptive thinking.
  2. If `stop_reason == "tool_use"`: execute each tool against the MCP server, append results, continue.
  3. If `stop_reason == "end_turn"`: parse the final text as `TriageDecision`. If validation fails, the result records `schema_valid=False`.
- Per-call usage (`input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`) is summed and converted to USD using per-million rates.

## Run it

```bash
make setup                    # uv sync (Python 3.11+ required)
export ANTHROPIC_API_KEY=...  # required; or set LLM_BACKEND=ollama once that's wired

# Triage one alert end-to-end
make run                      # defaults to ALERT-001
uv run python -m alert_triage.cli run ALERT-007   # specific alert id

# Run the full eval
make eval                     # 15 alerts, ~$0.05-0.15 with cache hits

# Tests (no LLM, no Docker)
make test
```

`make siem-up` brings up the SIEM mock from the sibling MCP project; `make run` and `make eval` invoke it as a prereq.

Prerequisites: Python 3.11+, [`uv`](https://docs.astral.sh/uv/), Docker, `ANTHROPIC_API_KEY`.

### Backend selection

| `LLM_BACKEND` | Model env var | Default | Notes |
|---|---|---|---|
| `anthropic` (default) | `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | The cost-effective default. Override with `claude-opus-4-7` for max intelligence. |
| `ollama` | `OLLAMA_MODEL`, `OLLAMA_HOST` | `qwen2.5:14b-instruct-q4_K_M` | Stubbed. Implementation queued behind the box rebuild. |

## Layout

```
agents/llm-alert-triage/
├── pyproject.toml
├── Makefile
├── data/
│   ├── alerts.jsonl              # 15 synthetic alerts
│   └── ground_truth.jsonl        # 15 labeled verdicts
├── src/alert_triage/
│   ├── schema.py                 # Pydantic + hand-written JSON schema
│   ├── llm.py                    # backend adapter (anthropic + ollama-stub)
│   ├── mcp_client.py             # spawn + connect to the MCP server
│   ├── agent.py                  # the manual agentic loop
│   ├── eval.py                   # scoring + cost + archival
│   └── cli.py                    # `make run` / `make eval` entry points
└── tests/
    ├── test_schema.py            # schema validation + dataset alignment
    └── test_mcp_tools.py         # MCP -> Anthropic tool conversion
```

## Interview-ready

_Filled in once enough eval runs are archived to discuss model-drift trends. Will document: risk reduced (analyst time vs accuracy floor), failure modes (model hallucination, schema drift, MCP server unreachable), detection (schema validity rate, per-class accuracy, anomalous cost spikes), rollback (deterministic eval set + git history of prompts), and scale (batch API for cost, prompt caching for repeat runs)._

## References

- [Anthropic Messages API — tool use](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- [Anthropic structured outputs (`output_config.format`)](https://docs.anthropic.com/en/docs/build-with-claude/structured-outputs)
- [Anthropic prompt caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)
- [Model Context Protocol](https://modelcontextprotocol.io)
- [MITRE ATT&CK](https://attack.mitre.org)
- [Pydantic](https://docs.pydantic.dev)
