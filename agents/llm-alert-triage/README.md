# LLM Alert Triage

A triage agent that consumes synthetic alerts, enriches them via the [MCP Security Tooling Server](../mcp-security-tooling/), and emits schema-validated triage decisions. Ships with an eval harness scoring accuracy, false-positive rate, schema validity, and reasoning quality on a labeled dataset.

**Status: WIP.** Skeleton.

---

## Problem

LLM-based alert triage is easy to demo and hard to trust. The interesting questions aren't "can the model write a verdict" but "how often is it wrong, in which direction, and how do you know when to stop trusting it?" That requires labeled data, a pinned schema, and an eval harness that runs in CI — not screenshots from a single prompt.

## What I built

- A triage agent (Anthropic API; Ollama backend optional via `LLM_BACKEND=ollama`) that ingests synthetic alerts and produces Pydantic-validated decisions: `severity`, `verdict`, `reasoning`, `recommended_actions`, `mitre_techniques`.
- A labeled synthetic dataset (~100 alerts across malware, credential abuse, lateral movement, and benign/false-positive cases) with ground-truth verdicts.
- An eval harness reporting accuracy, FP rate, schema-validation rate, and an LLM-as-judge reasoning-quality score against a pinned rubric.
- Tool calls into the MCP Security Tooling server for indicator enrichment and event search.
- Per-run cost and latency tracking.

## How it works

- **Input:** synthetic alert JSON (alert ID, source, signal, raw event payload).
- **Loop:** agent reads alert → optionally calls MCP tools (`enrich_indicator`, `search_events`) → produces a structured decision.
- **Schema:** Pydantic models reject malformed outputs before they reach scoring; schema-validation rate is itself a tracked metric.
- **Eval:** ground truth is human-labeled. Accuracy and FP rate are direct comparisons; reasoning quality uses LLM-as-judge with a pinned rubric and a documented judge model.
- **Determinism:** the seeded MCP backend means eval scores are reproducible across runs against the same model+prompt version.

## Run it

```bash
make setup
make run        # triage one alert end-to-end and pretty-print the trace
make eval       # full dataset, prints scoring summary and a per-class confusion matrix
make test
```

Prerequisites: Python 3.11+, `uv`, Docker (for the MCP server backing service), `ANTHROPIC_API_KEY` (or `LLM_BACKEND=ollama`).

## Interview-ready

_Filled in once Status reaches Stable. Will document: risk reduced, failure modes, detection, rollback, scale._

## References

- MITRE ATT&CK — https://attack.mitre.org
- Pydantic — https://docs.pydantic.dev
- Anthropic structured outputs — https://docs.anthropic.com
