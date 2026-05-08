# Resume blurbs — current portfolio

Working artifact. Match your existing resume style (project name in caps, 2 bullets, action verbs, results). All numbers below are backed by committed eval results in this repo.

If forced to pick two for limited resume space, lead with **LLM-Driven Alert Triage** (the cross-provider eval surfaced a real provider-asymmetric regression — a senior-level depth signal) and **AI Incident Response Copilot with Prompt-Injection Resistance** (the prompt-injection-aware story is what most "AI in SecOps" portfolios don't have).

---

## LLM-DRIVEN ALERT TRIAGE WITH MULTI-PROVIDER EVAL HARNESS
- Shipped a triage agent (Anthropic + OpenAI backends, Pydantic-typed outputs, prompt caching, adaptive thinking) that consumes synthetic SecOps alerts, enriches them via tool calls into a Model Context Protocol (MCP) server, and emits schema-validated decisions mapped to MITRE ATT&CK; both backends produce 100% schema-valid output across a 15-alert labeled dataset.
- Built an apples-to-apples cross-provider eval harness scoring verdict accuracy, severity calibration, MITRE technique IoU, latency, and per-call cost; surfaced a real engineering finding when a single prompt-tuning iteration improved OpenAI gpt-5-mini scores (+20pt severity, +0.17 MITRE IoU) but regressed Anthropic Sonnet 4.6 by 27 verdict points — exactly the kind of provider-asymmetric regression the multi-provider eval is built to catch.

## AI INCIDENT RESPONSE COPILOT WITH PROMPT-INJECTION RESISTANCE
- Built a single-turn IR copilot (Anthropic + OpenAI backends, structured-output JSON schema enforcement, Pydantic client-side validation) that ingests synthetic Slack-style incident transcripts and emits structured IR docs covering timeline, scope, indicators, action items, and comms draft; 100% status-field accuracy across 5 incident archetypes on both providers.
- Implemented a three-layer prompt-injection defense (data-not-instructions framing + schema-constrained output + injection-acknowledgement instruction) and a red-team eval verifying it: **6/6 red-team transcripts (status-flip, system-prompt-leak, destructive-action injection) defeated across both providers**; zero forbidden text leaked into any IR doc field on any run.

## MCP SECURITY TOOLING SERVER
- Designed and built a Model Context Protocol server exposing a synthetic SIEM/EDR API to LLM agents over stdio — auth-scoped tools, HMAC-chained tamper-evident audit log of every invocation, deterministic responses for reproducible eval runs.
- Demonstrated a SecOps-shaped agent integration surface portable across LLM providers and reviewable by a security team, with end-to-end verification (9/9 tests passing, working client demo) and a containerized backing service that ships with the repo.

## DETECTION-AS-CODE WITH PURPLE-TEAM VALIDATION
- Authored a Sigma detection corpus across 5 ATT&CK tactics, each rule paired with positive log fixtures (Atomic Red Team-shaped) and negative fixtures (benign noise that shares surface features); shipped an in-process Sigma evaluator with a recursive-descent condition-expression parser supporting `and`, `or`, `not`, parentheses, and wildcard selectors.
- Built a purple-team runner that asserts every rule fires on its positives and stays silent on its negatives, integrated into CI: **15/15 positives matched, 0/14 negatives incorrectly matched, 21/21 unit tests, 0 lint errors, 0 ATT&CK mapping warnings**. ATT&CK Navigator JSON export for coverage visibility; sigma-cli SPL conversion for SIEM deployment.
