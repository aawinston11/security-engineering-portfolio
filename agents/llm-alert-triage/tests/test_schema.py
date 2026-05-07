"""Schema validation tests — no LLM required."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from alert_triage.schema import (
    TRIAGE_OUTPUT_SCHEMA,
    Alert,
    GroundTruth,
    TriageDecision,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def test_triage_decision_valid_payload() -> None:
    payload = {
        "severity": "high",
        "verdict": "true_positive",
        "confidence": 0.85,
        "reasoning": "Encoded PowerShell with external indicator. Related event confirms staged download.",
        "recommended_actions": ["isolate host", "collect process tree"],
        "mitre_techniques": ["T1059.001", "T1105"],
    }
    decision = TriageDecision.model_validate(payload)
    assert decision.verdict == "true_positive"
    assert decision.mitre_techniques == ["T1059.001", "T1105"]


def test_triage_decision_rejects_unknown_verdict() -> None:
    with pytest.raises(ValidationError):
        TriageDecision.model_validate({
            "severity": "high",
            "verdict": "definitely_bad",  # not in Literal
            "confidence": 0.5,
            "reasoning": "...",
            "recommended_actions": ["..."],
            "mitre_techniques": [],
        })


def test_triage_decision_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        TriageDecision.model_validate({
            "severity": "low",
            "verdict": "benign",
            "confidence": 0.9,
            "reasoning": "...",
            "recommended_actions": ["..."],
            "mitre_techniques": [],
            "extra": "no",
        })


def test_output_schema_shape() -> None:
    """The hand-written JSON schema is structurally what the API expects."""
    s = TRIAGE_OUTPUT_SCHEMA
    assert s["type"] == "object"
    assert s["additionalProperties"] is False
    required = set(s["required"])
    properties = set(s["properties"])
    assert required == properties == {
        "severity", "verdict", "confidence", "reasoning",
        "recommended_actions", "mitre_techniques",
    }
    assert s["properties"]["severity"]["enum"] == [
        "critical", "high", "medium", "low", "info",
    ]


def test_alerts_dataset_parses() -> None:
    rows = [
        json.loads(line)
        for line in (DATA_DIR / "alerts.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert len(rows) == 15
    for row in rows:
        Alert.model_validate(row)


def test_ground_truth_dataset_parses_and_aligns() -> None:
    alerts = [
        Alert.model_validate_json(line)
        for line in (DATA_DIR / "alerts.jsonl").read_text().splitlines()
        if line.strip()
    ]
    truths = [
        GroundTruth.model_validate_json(line)
        for line in (DATA_DIR / "ground_truth.jsonl").read_text().splitlines()
        if line.strip()
    ]
    alert_ids = {a.alert_id for a in alerts}
    truth_ids = {t.alert_id for t in truths}
    assert alert_ids == truth_ids, "alerts.jsonl and ground_truth.jsonl must align by alert_id"
