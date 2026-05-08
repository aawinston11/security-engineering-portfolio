"""Emit MITRE ATT&CK Navigator JSON layer from the rule corpus.

The output is loadable at https://mitre-attack.github.io/attack-navigator/ via
"Open Existing Layer" -> "Upload from local". Each technique covered by at
least one rule gets `score: 100` and a comment listing the rules that cover it.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .loader import LoadedRule, load_rules


def build_layer(rules: list[LoadedRule], *, name: str = "Synthetic Detection Coverage") -> dict[str, Any]:
    by_technique: dict[str, list[str]] = defaultdict(list)
    for r in rules:
        for t in r.attack_techniques:
            by_technique[t].append(r.title)

    techniques = [
        {
            "techniqueID": t,
            "score": 100,
            "color": "",
            "comment": "Covered by: " + "; ".join(sorted(set(titles))),
            "enabled": True,
            "metadata": [],
            "showSubtechniques": True,
        }
        for t, titles in sorted(by_technique.items())
    ]

    return {
        "name": name,
        "versions": {
            "attack": "14",
            "navigator": "5.0.0",
            "layer": "4.5",
        },
        "domain": "enterprise-attack",
        "description": "ATT&CK Navigator coverage layer auto-generated from rules/.",
        "filters": {"platforms": ["Windows", "Linux", "macOS"]},
        "sorting": 0,
        "layout": {
            "layout": "side",
            "aggregateFunction": "average",
            "showID": False,
            "showName": True,
            "showAggregateScores": False,
            "countUnscored": False,
        },
        "hideDisabled": False,
        "techniques": techniques,
        "gradient": {
            "colors": ["#ffffff", "#66bb6a"],
            "minValue": 0,
            "maxValue": 100,
        },
        "legendItems": [
            {"color": "#66bb6a", "label": "Covered by at least one rule"},
        ],
        "metadata": [],
        "showTacticRowBackground": False,
        "tacticRowBackground": "#dddddd",
        "selectTechniquesAcrossTactics": True,
        "selectSubtechniquesWithParent": False,
    }


def write_layer(out_path: Path, layer: dict[str, Any]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(layer, indent=2))


def emit() -> Path:
    layer = build_layer(load_rules())
    out = Path(__file__).resolve().parents[2] / "build" / "attack-navigator-layer.json"
    write_layer(out, layer)
    return out
