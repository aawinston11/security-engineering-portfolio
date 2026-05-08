"""Schema + dataset alignment tests — no LLM required."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ir_copilot.schema import (
    IR_DOC_SCHEMA,
    GroundTruth,
    IRDoc,
    RedTeamExpectation,
    Transcript,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def test_ir_doc_valid_payload() -> None:
    payload = {
        "title": "Encoded PowerShell on finance03",
        "summary": "Credential compromise; contained.",
        "severity": "high",
        "status": "contained",
        "timeline": [
            {"timestamp": "2026-04-22T08:14Z", "actor": "pagerduty",
             "description": "Alert fired"},
        ],
        "scope": "finance03; user jsmith",
        "indicators": [
            {"type": "url", "value": "hxxp://malicious.example.invalid/payload",
             "context": "C2 staging URL"},
        ],
        "action_items": [
            {"priority": "high", "description": "Forensic image finance03",
             "owner_role": "platform"},
        ],
        "comms_draft": "Contained credential compromise on finance03.",
    }
    doc = IRDoc.model_validate(payload)
    assert doc.severity == "high"
    assert doc.status == "contained"
    assert len(doc.timeline) == 1


def test_ir_doc_rejects_unknown_status() -> None:
    with pytest.raises(ValidationError):
        IRDoc.model_validate({
            "title": "x", "summary": "x", "severity": "low",
            "status": "definitely-resolved",  # not in Literal
            "timeline": [], "scope": "x", "indicators": [],
            "action_items": [], "comms_draft": "x",
        })


def test_ir_doc_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        IRDoc.model_validate({
            "title": "x", "summary": "x", "severity": "low",
            "status": "active", "timeline": [], "scope": "x",
            "indicators": [], "action_items": [], "comms_draft": "x",
            "extra_field": "boom",
        })


def test_output_schema_shape() -> None:
    s = IR_DOC_SCHEMA
    assert s["type"] == "object"
    assert s["additionalProperties"] is False
    expected_keys = {
        "title", "summary", "severity", "status", "timeline",
        "scope", "indicators", "action_items", "comms_draft",
    }
    assert set(s["required"]) == set(s["properties"]) == expected_keys
    assert s["properties"]["status"]["enum"] == [
        "active", "investigating", "contained", "resolved", "false_alarm",
    ]


def test_transcripts_dataset_parses() -> None:
    rows = [
        Transcript.model_validate_json(line)
        for line in (DATA_DIR / "transcripts.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert len(rows) == 5


def test_redteam_dataset_parses() -> None:
    rows = [
        Transcript.model_validate_json(line)
        for line in (DATA_DIR / "redteam.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert len(rows) == 3
    for t in rows:
        assert t.injection_summary, f"{t.transcript_id} missing injection_summary"


def test_ground_truth_aligned_to_transcripts() -> None:
    transcripts = {
        json.loads(line)["transcript_id"]
        for line in (DATA_DIR / "transcripts.jsonl").read_text().splitlines()
        if line.strip()
    }
    truths = [
        GroundTruth.model_validate_json(line)
        for line in (DATA_DIR / "ground_truth.jsonl").read_text().splitlines()
        if line.strip()
    ]
    truth_ids = {t.transcript_id for t in truths}
    assert transcripts == truth_ids


def test_redteam_expectations_aligned() -> None:
    transcripts = {
        json.loads(line)["transcript_id"]
        for line in (DATA_DIR / "redteam.jsonl").read_text().splitlines()
        if line.strip()
    }
    expectations = [
        RedTeamExpectation.model_validate_json(line)
        for line in (DATA_DIR / "redteam_expectations.jsonl").read_text().splitlines()
        if line.strip()
    ]
    expectation_ids = {e.transcript_id for e in expectations}
    assert transcripts == expectation_ids
