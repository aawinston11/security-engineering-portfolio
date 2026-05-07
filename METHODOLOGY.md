# Portfolio methodology

This document spells out how the portfolio is built and maintained so the scope is well understood by readers and reviewers.

---

## AI-assisted, human-validated

- **Drafts** (configs, playbooks, detection rules, docs) may be generated or assisted by AI tools.
- **Every change that is “done”** is reviewed, tested, and verified by a human before it is considered complete.
- **Interview and audit** — You should be able to explain and defend every artifact; “AI wrote it” is not sufficient without understanding and validation.

This is explicitly called out so that:
- The portfolio is not presented as 100% hand-written from scratch.
- The bar is clear: human review and validation are required.
- It aligns with real-world use of AI in security engineering (drafting, consistency, boilerplate) while keeping accountability.

---

## Evidence-first

- **Baselines** — Capture state before changes (e.g. Lynis, config snapshots).
- **Runbooks and validation** — Use exact commands and expected outputs where possible.
- **Post-change evidence** — Store comparison outputs, scan results, and screenshots so improvements are demonstrable.

Evidence lives in project folders (e.g. `<project>/evidence/`) and is referenced in the project README.

---

## Enterprise lens

- **Controls over tweaks** — Prefer repeatable, documented controls (e.g. Ansible, policy) over one-off manual changes.
- **Repeatable automation** — Idempotent playbooks, pipelines, and scripts that can run in multiple environments.
- **Safe changes** — Backup before change, rollback guidance, and clear failure modes.
- **Operational realism** — Consider monitoring, alerting, and who runs what in production.

---

## Interview-ready

For significant changes we document:

- **Risk reduced** — What threat or finding does this address?
- **Failure modes** — What can go wrong (e.g. lockout, service break)?
- **Detection / monitoring** — How do we know if it’s working or broken?
- **Rollback** — How do we revert safely?
- **Scale implications** — How does this behave at 10 vs 1000 hosts?

This supports both “what did you do?” and “how would you run this at scale?” in interviews.

---

## Scope of the repo

- **In scope** — Security-focused artifacts across three pillars: AI/agentic security tooling, detection-as-code with closed-loop validation, and a small set of foundations (hardening, baseline ops).
- **Out of scope** — Anything that references real production infrastructure, customer telemetry, or employer systems. Sample data is synthetic and labeled as such.
- **Environment** — Each project ships runnable against synthetic inputs or a self-contained lab; nothing here requires access to a private homelab to reproduce.

---

## How to use this

- **Contributing (solo or future collaborators)** — Run changes through the same bar: draft → review → test → document (risk, failure modes, rollback).
- **Readers / interviewers** — You can assume artifacts that are “done” have been human-validated and that methodology is documented here and in the README.
