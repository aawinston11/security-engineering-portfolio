"""Purple-team runner: for each rule, fire its should_match fixtures (positive cases)
and should_not_match fixtures (negative cases) through the in-process Sigma
evaluator and assert the rule's detection logic produces the expected hits.

This is the same shape as a real purple-team run (technique fixture -> SIEM ->
detection assertion), but the SIEM is replaced by a deterministic in-process
matcher so the run is reproducible in CI without a Splunk/ES container.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .loader import LoadedRule, load_rules
from .sigma_runtime import matches


@dataclass
class RuleResult:
    rule_id: str
    title: str
    techniques: list[str] = field(default_factory=list)
    positives_total: int = 0
    positives_matched: int = 0
    negatives_total: int = 0
    negatives_matched: int = 0  # negatives that incorrectly matched
    failures: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return (
            self.positives_matched == self.positives_total
            and self.negatives_matched == 0
        )


def evaluate_rule(rule: LoadedRule) -> RuleResult:
    result = RuleResult(
        rule_id=rule.rule_id,
        title=rule.title,
        techniques=rule.attack_techniques,
        positives_total=len(rule.should_match),
        negatives_total=len(rule.should_not_match),
    )

    for i, event in enumerate(rule.should_match):
        try:
            hit = matches(rule.rule, event)
        except Exception as e:  # noqa: BLE001
            result.failures.append(f"positive[{i}] evaluator error: {type(e).__name__}: {e}")
            continue
        if hit:
            result.positives_matched += 1
        else:
            result.failures.append(
                f"positive[{i}] DID NOT match: "
                f"atomic_test_id={event.get('_atomic_test_id', '?')}"
            )

    for i, event in enumerate(rule.should_not_match):
        try:
            hit = matches(rule.rule, event)
        except Exception as e:  # noqa: BLE001
            result.failures.append(f"negative[{i}] evaluator error: {type(e).__name__}: {e}")
            continue
        if hit:
            result.negatives_matched += 1
            note = event.get("_note", "")
            result.failures.append(f"negative[{i}] INCORRECTLY matched: {note!r}")

    return result


def run_purple_team() -> list[RuleResult]:
    return [evaluate_rule(r) for r in load_rules()]
