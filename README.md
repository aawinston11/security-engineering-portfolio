# Security Engineering Portfolio

**Secure by default. Automated by design.**

Security operations engineer (8 years, CISSP) focused on AI-augmented detection, response, and platform tooling for SecOps. This is the public-facing version of work I do day-to-day: agentic security tooling, detection-as-code with closed-loop validation, and the small handful of foundations that hold it all up.

Work is **AI-assisted, human-validated**. Sample data is synthetic; nothing here references any employer system, customer telemetry, or production network.

---

## Flagship projects

### Agents — AI / agentic security (the headline pillar)

| Project | Status | One-liner |
|---|---|---|
| [MCP Security Tooling Server](agents/mcp-security-tooling/) | WIP | MCP server exposing a synthetic SIEM/EDR API to LLM agents — auth-scoped tools, deterministic responses, audit trail. One tool live; tested end-to-end (9/9 tests + demo verified). |
| [LLM Alert Triage](agents/llm-alert-triage/) | Beta | Triage agent over Anthropic + OpenAI backends; consumes synthetic alerts, enriches via the MCP server, emits schema-validated decisions. Eval harness scores accuracy, FP rate, IoU, latency, and per-call cost on a labeled dataset. Both backends live-verified, 100% schema validity. Untuned baselines: Anthropic 67% verdict accuracy / $0.26; OpenAI 53% / $0.06. Comparison table in the project README. |
| [IR Copilot](agents/ir-copilot/) | Beta | Ingests a synthetic incident-channel transcript and produces a structured IR doc. Three-layer prompt-injection defense (data-not-instructions framing + schema-constrained output + injection acknowledgement). Live-verified on Anthropic + OpenAI: **6/6 red-team cases passed on both backends** (status-flip, prompt-leak, destructive-action injection). 100% status accuracy on the happy path. Comparison table in the project README. |

### Detection & automation

| Project | Status | One-liner |
|---|---|---|
| [Detection-as-Code](detection/detection-as-code/) | Beta | 5 Sigma rules across 5 ATT&CK tactics, each with positive (Atomic Red Team-shaped) and negative log fixtures. In-process Sigma evaluator + purple-team runner asserts every rule fires on its positives and stays silent on its negatives. **15/15 positives matched, 0/14 negatives incorrectly matched.** Lint, ATT&CK mapping validation, Navigator JSON export, sigma-cli SPL conversion, 21/21 unit tests. |

### Foundations

| Project | Status | One-liner |
|---|---|---|
| [Linux Hardening Role](foundations/linux-hardening-role/) | Beta | Idempotent Ansible role for Ubuntu 22.04 baseline (SSH, UFW, PAM, auditd, fail2ban, kernel), with Lynis baseline/post evidence and rollback. |

---

## Methodology, in three lines

- **AI-assisted, human-validated.** Drafts can be model-written; nothing ships without human review and a working test.
- **Evidence-first.** Baseline → change → post evidence; runbooks specify exact commands and expected outputs.
- **Interview-ready.** Every project documents risk reduced, failure modes, detection, rollback, and scale.

Full methodology: [METHODOLOGY.md](METHODOLOGY.md). Per-project template: [notes/_TEMPLATE.md](notes/_TEMPLATE.md).

---

## Run any project

Each project ships a `Makefile` with the same surface:

```bash
make setup    # install deps (uv-managed Python; Docker for SIEM/EDR mocks)
make run      # run against synthetic data
make eval     # only on projects with an eval harness
make test     # unit + integration
```

Configure API keys once at the repo root: `cp .env.example .env` and fill it in. `.env` is gitignored. Shell exports also work and take precedence. Agent projects need `ANTHROPIC_API_KEY` and/or `OPENAI_API_KEY` (selected via `LLM_BACKEND=anthropic|openai`); `LLM_BACKEND=ollama` is stubbed pending the LLM lab box rebuild. The hardening role needs Ansible 2.14+ and an Ubuntu 22.04 target VM.

---

## What's not here

No 16-phase learning roadmap. No GRC compliance walkthrough. No SPF/DKIM/DMARC tutorial. Those skills exist; they don't differentiate, so they don't lead.
