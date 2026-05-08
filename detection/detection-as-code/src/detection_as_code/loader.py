"""Load Sigma rules and per-rule fixtures from the rules/ tree."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

RULES_DIR = Path(__file__).resolve().parents[2] / "rules"


@dataclass
class LoadedRule:
    rule_path: Path
    rule_dir: Path
    rule: dict[str, Any]
    should_match: list[dict[str, Any]] = field(default_factory=list)
    should_not_match: list[dict[str, Any]] = field(default_factory=list)

    @property
    def rule_id(self) -> str:
        return self.rule.get("id", "<unknown>")

    @property
    def title(self) -> str:
        return self.rule.get("title", "<untitled>")

    @property
    def attack_techniques(self) -> list[str]:
        techniques: list[str] = []
        for tag in self.rule.get("tags", []):
            if not isinstance(tag, str):
                continue
            if tag.startswith("attack.t") and not tag.startswith("attack.ta"):
                # attack.t1059.001 -> T1059.001
                techniques.append(tag.split(".", 1)[1].upper().replace("T", "T", 1))
        return techniques

    @property
    def attack_tactics(self) -> list[str]:
        return [
            tag.split(".", 1)[1]
            for tag in self.rule.get("tags", [])
            if isinstance(tag, str) and tag.startswith("attack.")
            and not tag.startswith("attack.t")
        ]


def load_rules(rules_dir: Path = RULES_DIR) -> list[LoadedRule]:
    """Walk rules_dir and load every rule.yml + its companion fixtures."""
    out: list[LoadedRule] = []
    for rule_path in sorted(rules_dir.rglob("rule.yml")):
        rule_dir = rule_path.parent
        with rule_path.open() as f:
            rule = yaml.safe_load(f)

        out.append(LoadedRule(
            rule_path=rule_path,
            rule_dir=rule_dir,
            rule=rule,
            should_match=_load_jsonl(rule_dir / "should_match.jsonl"),
            should_not_match=_load_jsonl(rule_dir / "should_not_match.jsonl"),
        ))
    return out


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line) for line in path.read_text().splitlines() if line.strip()
    ]
