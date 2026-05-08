"""Static checks on the rule corpus.

Each check is independent and accumulates findings instead of failing fast, so
a single `make lint` run surfaces every issue.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .loader import LoadedRule

REQUIRED_FIELDS = ("title", "id", "status", "description", "logsource", "detection",
                   "tags", "level")
ALLOWED_LEVELS = {"informational", "low", "medium", "high", "critical"}
ALLOWED_STATUSES = {"experimental", "test", "stable", "deprecated", "unsupported"}
ATTACK_TECHNIQUE_RE = re.compile(r"^attack\.t\d{4}(\.\d{3})?$")


@dataclass
class Finding:
    rule_id: str
    rule_path: str
    severity: str  # "error" | "warning"
    message: str

    def __str__(self) -> str:
        return f"  [{self.severity}] {self.rule_id} ({self.rule_path}): {self.message}"


def lint_rules(rules: list[LoadedRule]) -> list[Finding]:
    findings: list[Finding] = []
    seen_ids: dict[str, str] = {}

    for r in rules:
        path_str = str(r.rule_path.relative_to(r.rule_path.parents[3]))
        rid = r.rule_id

        for f in REQUIRED_FIELDS:
            if f not in r.rule:
                findings.append(Finding(rid, path_str, "error",
                                        f"missing required field: {f!r}"))

        if rid in seen_ids:
            findings.append(Finding(rid, path_str, "error",
                                    f"duplicate id; also used by {seen_ids[rid]}"))
        else:
            seen_ids[rid] = path_str

        level = r.rule.get("level")
        if level and level not in ALLOWED_LEVELS:
            findings.append(Finding(rid, path_str, "error",
                                    f"level {level!r} not in {sorted(ALLOWED_LEVELS)}"))

        status = r.rule.get("status")
        if status and status not in ALLOWED_STATUSES:
            findings.append(Finding(rid, path_str, "warning",
                                    f"non-standard status {status!r}"))

        tags = r.rule.get("tags", [])
        attack_tech_tags = [t for t in tags
                            if isinstance(t, str) and t.startswith("attack.t")]
        if not attack_tech_tags:
            findings.append(Finding(rid, path_str, "error",
                                    "no attack.tNNNN tag — every rule must map to "
                                    "at least one ATT&CK technique"))
        for t in attack_tech_tags:
            if not ATTACK_TECHNIQUE_RE.match(t):
                findings.append(Finding(rid, path_str, "error",
                                        f"malformed attack tag {t!r} — expected "
                                        "attack.tNNNN[.NNN]"))

        # Detection block must reference at least one selection in `condition`.
        det = r.rule.get("detection", {})
        if "condition" not in det:
            findings.append(Finding(rid, path_str, "error",
                                    "detection block missing 'condition'"))

        # Fixtures: must have at least one positive and one negative.
        if not r.should_match:
            findings.append(Finding(rid, path_str, "error",
                                    "no should_match.jsonl fixtures — every rule "
                                    "needs at least one positive case for purple-team"))
        if not r.should_not_match:
            findings.append(Finding(rid, path_str, "warning",
                                    "no should_not_match.jsonl fixtures — every rule "
                                    "should also have at least one negative case"))

    return findings
