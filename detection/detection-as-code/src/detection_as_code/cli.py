"""CLI: lint | validate-attack-mappings | purple-team | navigator | convert-spl."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from .lint import lint_rules
from .loader import load_rules
from .navigator import emit as emit_navigator
from .purple_team import run_purple_team

RULES_DIR = Path(__file__).resolve().parents[2] / "rules"
SPL_OUT = Path(__file__).resolve().parents[2] / "generated-spl"


def cmd_lint() -> int:
    rules = load_rules()
    print(f"Loaded {len(rules)} rule(s) from {RULES_DIR}")
    findings = lint_rules(rules)
    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]
    for f in findings:
        print(str(f))
    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


def cmd_validate_attack_mappings() -> int:
    """All rules must have at least one well-formed attack.tNNNN tag.
    Tactical tag (attack.execution etc.) recommended but not required by lint."""
    rules = load_rules()
    bad: list[str] = []
    for r in rules:
        if not r.attack_techniques:
            bad.append(r.rule_id)
    if bad:
        print(f"  rules missing ATT&CK technique mapping: {bad}")
        return 1
    print(f"  all {len(rules)} rules have at least one ATT&CK technique mapping")
    return 0


def cmd_purple_team() -> int:
    results = run_purple_team()
    print(f"Running purple-team validation against {len(results)} rule(s):\n")
    overall_pass = True
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        marker = "OK" if r.passed else "X "
        techs = ",".join(r.techniques) or "(no technique tags)"
        print(
            f"  [{marker}] {r.rule_id} {techs}\n"
            f"      title: {r.title}\n"
            f"      positives: {r.positives_matched}/{r.positives_total} matched"
            f" | negatives: {r.negatives_matched} unexpected hits "
            f"of {r.negatives_total} {status}"
        )
        if r.failures:
            for f in r.failures:
                print(f"      - {f}")
        if not r.passed:
            overall_pass = False
    total_positives = sum(r.positives_total for r in results)
    matched_positives = sum(r.positives_matched for r in results)
    total_negatives = sum(r.negatives_total for r in results)
    bad_negatives = sum(r.negatives_matched for r in results)
    print(
        f"\nSummary: {matched_positives}/{total_positives} positives matched, "
        f"{bad_negatives}/{total_negatives} negatives incorrectly matched."
    )
    return 0 if overall_pass else 1


def cmd_navigator() -> int:
    out = emit_navigator()
    print(f"Wrote {out.relative_to(Path.cwd()) if out.is_relative_to(Path.cwd()) else out}")
    print("Load via https://mitre-attack.github.io/attack-navigator/ -> Open Existing Layer.")
    return 0


def cmd_convert_spl() -> int:
    """Convert each Sigma rule to SPL using sigma-cli's splunk backend.
    Output goes to generated-spl/. Requires `sigma-cli` and the splunk backend
    plugin (installed via the dev extra)."""
    sigma_bin = shutil.which("sigma")
    if not sigma_bin:
        print("sigma-cli not on PATH. Install with `make setup` or `uv add --dev sigma-cli`.")
        return 1

    SPL_OUT.mkdir(parents=True, exist_ok=True)
    rules = load_rules()
    failed: list[str] = []
    for r in rules:
        rel = r.rule_path.relative_to(RULES_DIR)
        out_path = SPL_OUT / rel.with_suffix(".spl")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [sigma_bin, "convert", "-t", "splunk", "-f", "default", "-o", str(out_path),
               str(r.rule_path)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            failed.append(f"{rel}: {proc.stderr.strip()}")
            continue
        print(f"  wrote {out_path.relative_to(Path.cwd()) if out_path.is_relative_to(Path.cwd()) else out_path}")

    if failed:
        print("\nFailures:")
        for f in failed:
            print(f"  - {f}")
        return 1
    print(f"\nConverted {len(rules)} rule(s) to SPL.")
    return 0


USAGE = """\
usage: python -m detection_as_code.cli {lint | validate-attack-mappings | purple-team | navigator | convert-spl}

Commands:
  lint                       Schema check on every rule (required fields, levels, ATT&CK tags, fixtures)
  validate-attack-mappings   Assert every rule has at least one ATT&CK technique tag
  purple-team                Replay positive + negative fixtures through the Sigma evaluator
  navigator                  Emit ATT&CK Navigator JSON layer (build/attack-navigator-layer.json)
  convert-spl                Convert each rule to Splunk SPL via sigma-cli (writes generated-spl/)

Examples:
  uv run python -m detection_as_code.cli lint
  uv run python -m detection_as_code.cli purple-team
  uv run python -m detection_as_code.cli navigator
"""


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(USAGE, file=sys.stderr)
        sys.exit(2)
    if args[0] in ("--help", "-h", "help"):
        print(USAGE)
        sys.exit(0)
    cmd = args[0]
    funcs = {
        "lint": cmd_lint,
        "validate-attack-mappings": cmd_validate_attack_mappings,
        "purple-team": cmd_purple_team,
        "navigator": cmd_navigator,
        "convert-spl": cmd_convert_spl,
    }
    if cmd not in funcs:
        print(f"unknown command: {cmd!r}\n\n{USAGE}", file=sys.stderr)
        sys.exit(2)
    sys.exit(funcs[cmd]())


if __name__ == "__main__":
    main()
