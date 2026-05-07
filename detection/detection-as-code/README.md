# Detection-as-Code

Sigma + Splunk SPL detections under version control with CI lint/validation, MITRE ATT&CK mapped, plus a purple-team runner that fires Atomic Red Team techniques against a containerized log generator and asserts the corresponding detection triggers.

**Status: WIP.** Skeleton.

---

## Problem

Most detection content is paste-into-the-console-and-pray: no review, no tests, no link between "we wrote a rule for T1059.001" and "T1059.001 actually fires the rule." This project closes the loop — detections are code, they're tested, and the test is the real adversary technique.

## What I built

- Detection corpus organized by ATT&CK tactic: each rule lives in `rules/<tactic>/<technique>/` with Sigma source, generated Splunk SPL, ATT&CK metadata, and a test fixture.
- CI: `sigma-cli` validation, SPL syntax check, ATT&CK ID/technique cross-validation, no-orphan-rule check (every rule has a test fixture).
- Purple-team runner: spins up a containerized log generator, fires an Atomic Red Team technique, queries the SPL rule against the resulting logs, and asserts ≥1 detection record is produced.
- Coverage map exported as a MITRE ATT&CK Navigator JSON layer.

## How it works

- **Authoring:** rules in Sigma; SPL is generated and committed (so the deployed artifact is reviewable).
- **CI:** GitHub Actions runs lint + ATT&CK mapping checks on every PR. PRs without a test fixture fail.
- **Validation loop:** for each rule, the runner picks the Atomic Red Team test matching the technique, executes it inside an isolated container, ships logs to a Splunk-compatible index, runs the SPL, and asserts a hit. Result: a detection has either passed validation against a real technique or it hasn't — no third option.
- **Coverage:** Navigator JSON produced from rule metadata; renderable on https://mitre-attack.github.io/attack-navigator/.

## Run it

```bash
make setup
make lint           # Sigma + SPL + ATT&CK mapping checks
make validate       # purple-team loop on a single technique
make validate-all   # purple-team loop on the full corpus (slower)
make navigator      # emit ATT&CK Navigator JSON to ./build/
make test
```

Prerequisites: Python 3.11+, `uv`, Docker, a Splunk-compatible search backend (Splunk Enterprise free tier or compatible stand-in).

## Interview-ready

_Filled in once Status reaches Stable. Will document: risk reduced, failure modes, detection, rollback, scale._

## References

- MITRE ATT&CK — https://attack.mitre.org
- Sigma — https://github.com/SigmaHQ/sigma
- Atomic Red Team — https://github.com/redcanaryco/atomic-red-team
- ATT&CK Navigator — https://mitre-attack.github.io/attack-navigator/
- MITRE D3FEND — https://d3fend.mitre.org
