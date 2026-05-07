# Security Engineering Portfolio

**Secure by default. Automated by design.**

Security operations engineer (8 years, CISSP) focused on AI-augmented detection, response, and platform tooling for SecOps. This is the public-facing version of work I do day-to-day: agentic security tooling, detection-as-code with closed-loop validation, and the small handful of foundations that hold it all up.

Work is **AI-assisted, human-validated**. Sample data is synthetic; nothing here references any employer system, customer telemetry, or production network.

---

## Flagship projects

### Agents — AI / agentic security (the headline pillar)

| Project | Status | One-liner |
|---|---|---|
| [MCP Security Tooling Server](agents/mcp-security-tooling/) | WIP | MCP server exposing a synthetic SIEM/EDR API to LLM agents — auth-scoped tools, deterministic responses, audit trail. |
| [LLM Alert Triage](agents/llm-alert-triage/) | WIP | Triage agent that consumes synthetic alerts, enriches via the MCP server, and emits schema-validated decisions. Eval harness scores accuracy, FP rate, and reasoning quality on a labeled dataset. |
| [IR Copilot](agents/ir-copilot/) | WIP | Ingests a synthetic incident-channel transcript and produces a structured IR doc + action items. Prompt-injection guardrails for untrusted input. |

### Detection & automation

| Project | Status | One-liner |
|---|---|---|
| [Detection-as-Code](detection/detection-as-code/) | WIP | Sigma + Splunk SPL rules under CI with MITRE ATT&CK mapping, plus a purple-team runner that fires Atomic Red Team techniques and asserts the corresponding detection triggers. |

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

Prerequisites for agent projects: `ANTHROPIC_API_KEY`, or set `LLM_BACKEND=ollama` for a local model. Prerequisites for the hardening role: Ansible 2.14+ and an Ubuntu 22.04 target VM.

---

## What's not here

No 16-phase learning roadmap. No GRC compliance walkthrough. No SPF/DKIM/DMARC tutorial. Those skills exist; they don't differentiate, so they don't lead.
