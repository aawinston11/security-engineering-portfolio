# LLM Alert Triage

A triage agent that consumes synthetic alerts, enriches them via the [MCP Security Tooling Server](../mcp-security-tooling/), and emits schema-validated triage decisions. Ships with an eval harness scoring accuracy, false-positive rate, schema validity, and per-call cost/latency on a labeled 15-alert dataset.

**Status: Beta on Anthropic; OpenAI re-verification pending.** First live `make eval` run on Anthropic completed cleanly: 15/15 alerts processed, 100% schema validity, 66.7% verdict accuracy baseline, $0.26 for the run. OpenAI backend ran but only 6/15 alerts succeeded — the remainder hit `404 - Your organization must be verified to use the model gpt-5-mini` while permissions are still propagating post-verification (per OpenAI's documented 15-minute rollout). Re-run pending. Ollama backend is stubbed pending the LLM lab box rebuild. Unit tests: 14/14 pass.

---

## Problem

LLM-based alert triage is easy to demo and hard to trust. The interesting questions aren't "can the model write a verdict" but "how often is it wrong, in which direction, and how do you know when to stop trusting it?" That requires labeled data, a pinned schema, and an eval harness that runs in CI — not screenshots from a single prompt. Running the same eval against multiple providers also surfaces which one's worth what you pay for it.

## What's shipped

- **Hybrid LLM client.** Three backends, selected via `LLM_BACKEND`:
  - `anthropic` (default): Anthropic API. Default model `claude-sonnet-4-6`. Adaptive thinking + `effort=medium`. Prompt caching on the system prompt + tool schemas.
  - `openai`: OpenAI Chat Completions API. Default model `gpt-5-mini`. `reasoning_effort=medium` (configurable). `response_format=json_schema` with `strict: true`.
  - `ollama`: stub. Implementation queued behind the box rebuild.
- **Each backend owns its own agent loop.** Anthropic content blocks and OpenAI flat tool_calls don't translate cleanly through one shape, so the orchestrator (`agent.py`) is thin and each backend's `run_triage()` runs the loop in its provider-native style. Manual loops, not the SDK tool runners — explicit control over per-step audit, cost tracking, and termination.
- **Pydantic-validated decisions.** The Anthropic path uses `output_config.format` JSON schema; the OpenAI path uses strict `response_format` JSON schema. Both go through Pydantic on the client side for the constraints the API schema can't express (Literal enums, `extra=forbid`).
- **15-alert labeled dataset.** Maps into the MCP server's seeded event corpus: 8 true positives, 3 needs_investigation, 2 false positives, 2 benign. Ambiguous cases require tool-driven enrichment.
- **Eval harness.** Per-alert verdict accuracy, severity accuracy, MITRE technique IoU, schema-validation rate, false-positive rate, latency, per-call cost (with provider-specific cache adjustments). Results archived to `eval-results/eval-<timestamp>.json`. Same harness, both providers — apples to apples.

## How it works

```
                                                     [ MCP server ]
                                                     stdio subprocess
                                                            |
                                                            v
[ alert.json ] -> [ orchestrator ] --> [ LLMBackend.run_triage() ] -> [ TriageDecision ]
                       |                       |
                       |                       +-- AnthropicBackend (tool_use blocks, output_config.format)
                       |                       +-- OpenAIBackend    (tool_calls, response_format json_schema)
                       |                       +-- OllamaBackend    (stub)
                       |
                       +-- async execute_tool callback (calls MCP search_events etc.)
```

- Orchestrator (`agent.py`) lists MCP tools, converts each to a backend-agnostic `GenericTool`, and hands the loop to `llm.run_triage(...)` along with an `execute_tool` callback.
- Each backend translates `GenericTool` into its provider's tool schema, runs the loop until the final structured response, then returns a `TriageRunResult` with usage breakdown and the parsed `TriageDecision` (or schema-failure error).
- Per-call usage (`input_tokens`, `output_tokens`, `cached_tokens`, `cache_creation_tokens`, `reasoning_tokens`) is summed and converted to USD using per-(backend,model) rates.

## Run it

```bash
make setup                                                 # uv sync (Python 3.11+)

# Configure keys: copy .env.example to .env at the repo root, fill in your keys.
# (Shell exports also work and take precedence over .env.)
cp ../../.env.example ../../.env
$EDITOR ../../.env

# Anthropic (default)
make eval                                                  # 15 alerts, ~$0.05-0.15 with cache hits

# OpenAI
LLM_BACKEND=openai make eval                               # same dataset, same scoring

# Specific model override (env var or .env)
ANTHROPIC_MODEL=claude-opus-4-7 make eval
LLM_BACKEND=openai OPENAI_MODEL=gpt-5 make eval

# Single alert
make run                                                   # ALERT-001 by default
uv run python -m alert_triage.cli run ALERT-007            # specific alert id

# Tests (no LLM, no Docker)
make test
```

`make siem-up` brings up the SIEM mock from the sibling MCP project; `run` and `eval` invoke it as a prereq.

Prerequisites: Python 3.11+, [`uv`](https://docs.astral.sh/uv/), Docker, plus `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` depending on which backend you select. Keys are picked up from a repo-root `.env` file (gitignored; copy `.env.example` to start) or from your shell environment.

### Backend selection summary

| `LLM_BACKEND` | Model env | Default | Reasoning knob | API key |
|---|---|---|---|---|
| `anthropic` (default) | `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | `thinking={"type":"adaptive"}`, `effort=medium` | `ANTHROPIC_API_KEY` |
| `openai` | `OPENAI_MODEL` | `gpt-5-mini` | `OPENAI_REASONING_EFFORT=medium` (set empty to omit) | `OPENAI_API_KEY` |
| `ollama` | `OLLAMA_MODEL`, `OLLAMA_HOST` | `qwen2.5:14b-instruct-q4_K_M` | (stub) | (none) |

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
│   ├── llm.py                    # backend protocol + Anthropic/OpenAI/Ollama
│   ├── mcp_client.py             # spawn + connect to the MCP server
│   ├── agent.py                  # thin orchestrator (lists tools, delegates loop)
│   ├── eval.py                   # scoring + cost + archival
│   └── cli.py                    # `make run` / `make eval` entry points
└── tests/
    ├── test_schema.py            # schema validation + dataset alignment
    ├── test_mcp_tools.py         # MCP -> Anthropic tool conversion
    └── test_backends.py          # LLM_BACKEND selection
```

## Interview-ready

_Filled in once enough eval runs are archived to discuss model-drift trends across providers. Will document: risk reduced, failure modes (model hallucination, schema drift, MCP server unreachable, provider-specific tool-call shape regressions), detection (schema validity rate, per-class accuracy, anomalous cost spikes), rollback (deterministic eval set + git history of prompts), and scale (Anthropic batch API, OpenAI batch API, prompt caching for repeat runs)._

## References

- [Anthropic Messages API — tool use](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- [Anthropic structured outputs (`output_config.format`)](https://docs.anthropic.com/en/docs/build-with-claude/structured-outputs)
- [Anthropic prompt caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)
- [OpenAI function calling](https://platform.openai.com/docs/guides/function-calling)
- [OpenAI structured outputs](https://platform.openai.com/docs/guides/structured-outputs)
- [Model Context Protocol](https://modelcontextprotocol.io)
- [MITRE ATT&CK](https://attack.mitre.org)
- [Pydantic](https://docs.pydantic.dev)
