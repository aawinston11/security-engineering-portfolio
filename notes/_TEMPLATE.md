# <Project name>

<One-line elevator pitch.>

**Status: <WIP | Beta | Stable>.**

---

## Problem

<2-4 sentences. What gap does this close? Why does it matter to a SecOps team?>

## What I built

<Bullet list of concrete artifacts. No marketing voice. No "passionate about" language.>

## How it works

<Architecture in one diagram or five bullets. Call out the design decisions that aren't obvious — model choice, output schema, auth model, eval methodology, failure handling.>

## Run it

```bash
make setup
make run
make eval     # if applicable
make test
```

Prerequisites: <Python version, Docker, env vars, target system>.

## Interview-ready

- **Risk reduced:** <what threat or control gap this addresses>
- **Failure modes:** <what breaks, how you'd notice, blast radius>
- **Detection / monitoring:** <metrics, logs, eval signals — how you know it's working or has regressed>
- **Rollback:** <how you revert; recovery time>
- **Scale:** <behavior at 10x and 100x — bottlenecks, sharding, queueing, model cost>

## References

<Real frameworks by name and ID. MITRE ATT&CK technique IDs, NIST 800-53 controls, CIS benchmark sections, RFCs, vendor docs.>
