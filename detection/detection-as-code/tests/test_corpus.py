"""Sanity tests against the actual rule corpus — every rule lints clean,
purple-team passes 100%, and the navigator export is well-formed."""
from __future__ import annotations

from detection_as_code.lint import lint_rules
from detection_as_code.loader import load_rules
from detection_as_code.navigator import build_layer
from detection_as_code.purple_team import run_purple_team


def test_corpus_loads() -> None:
    rules = load_rules()
    assert len(rules) >= 4, "expected at least 4 rules in the corpus"
    for r in rules:
        assert r.attack_techniques, f"{r.rule_id} has no ATT&CK technique tags"


def test_corpus_lints_clean() -> None:
    rules = load_rules()
    findings = lint_rules(rules)
    errors = [f for f in findings if f.severity == "error"]
    assert errors == [], f"unexpected lint errors:\n" + "\n".join(str(e) for e in errors)


def test_corpus_purple_team_passes() -> None:
    results = run_purple_team()
    failed = [r for r in results if not r.passed]
    msg = "\n".join(
        f"  {r.rule_id} ({r.title}): {r.failures}" for r in failed
    )
    assert not failed, f"purple-team failures:\n{msg}"


def test_navigator_layer_well_formed() -> None:
    layer = build_layer(load_rules())
    assert layer["domain"] == "enterprise-attack"
    assert isinstance(layer["techniques"], list)
    assert len(layer["techniques"]) > 0
    for t in layer["techniques"]:
        assert t["techniqueID"].startswith("T")
        assert t["score"] == 100
        assert "Covered by" in t["comment"]
