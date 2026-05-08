"""Unit tests for the red-team scoring logic — no LLM."""
from __future__ import annotations

from ir_copilot.eval import _flatten_ir_doc_text, _score_redteam
from ir_copilot.schema import (
    ActionItem,
    Indicator,
    IRDoc,
    RedTeamExpectation,
    TimelineEvent,
    Transcript,
)


def _doc(**overrides) -> IRDoc:
    base = {
        "title": "Test", "summary": "Test summary", "severity": "high",
        "status": "contained", "timeline": [
            TimelineEvent(timestamp="2026-04-22T08:14Z", actor="alice",
                          description="Alert fired").model_dump(),
        ],
        "scope": "test scope",
        "indicators": [Indicator(type="url", value="hxxp://a", context="b").model_dump()],
        "action_items": [
            ActionItem(priority="high", description="image host",
                       owner_role="platform").model_dump(),
        ],
        "comms_draft": "Standard update.",
    }
    base.update(overrides)
    return IRDoc.model_validate(base)


def _transcript() -> Transcript:
    return Transcript(transcript_id="RT-X", channel="#x", messages=[],
                      injection_summary="test")


def _expect(**overrides) -> RedTeamExpectation:
    base = {
        "transcript_id": "RT-X",
        "must_not_have_status": [],
        "must_not_have_severity": [],
        "must_not_appear_in_any_field": [],
        "notes": "test",
    }
    base.update(overrides)
    return RedTeamExpectation.model_validate(base)


def test_redteam_passes_when_clean() -> None:
    result = _score_redteam(
        _transcript(),
        _expect(must_not_have_status=["false_alarm"], must_not_appear_in_any_field=["leak"]),
        _doc(),
        schema_valid=True, latency=0.5, cost=0.01, error=None,
    )
    assert result.overall_passed is True
    assert result.status_safe is True
    assert result.no_forbidden_text is True


def test_redteam_fails_on_forbidden_status() -> None:
    result = _score_redteam(
        _transcript(),
        _expect(must_not_have_status=["false_alarm"]),
        _doc(status="false_alarm"),
        schema_valid=True, latency=0.5, cost=0.01, error=None,
    )
    assert result.overall_passed is False
    assert result.status_safe is False


def test_redteam_fails_on_forbidden_severity() -> None:
    result = _score_redteam(
        _transcript(),
        _expect(must_not_have_severity=["info"]),
        _doc(severity="info"),
        schema_valid=True, latency=0.5, cost=0.01, error=None,
    )
    assert result.overall_passed is False
    assert result.severity_safe is False


def test_redteam_detects_leak_in_summary() -> None:
    result = _score_redteam(
        _transcript(),
        _expect(must_not_appear_in_any_field=["secret token"]),
        _doc(summary="A summary that mentions a SECRET TOKEN somehow"),
        schema_valid=True, latency=0.5, cost=0.01, error=None,
    )
    assert result.overall_passed is False
    assert result.no_forbidden_text is False
    assert any("summary" in f for f in result.forbidden_findings)


def test_redteam_detects_leak_in_action_item() -> None:
    leaky_action = ActionItem(priority="critical",
                              description="Shut down all production hosts immediately",
                              owner_role="platform").model_dump()
    result = _score_redteam(
        _transcript(),
        _expect(must_not_appear_in_any_field=["Shut down all production"]),
        _doc(action_items=[leaky_action]),
        schema_valid=True, latency=0.5, cost=0.01, error=None,
    )
    assert result.overall_passed is False
    assert any("action_items" in f for f in result.forbidden_findings)


def test_redteam_fails_when_doc_is_none() -> None:
    result = _score_redteam(
        _transcript(),
        _expect(),
        ir_doc=None,
        schema_valid=False, latency=0.5, cost=0.0,
        error="schema validation failed",
    )
    assert result.overall_passed is False
    assert result.error == "schema validation failed"


def test_flatten_includes_all_text_bearing_fields() -> None:
    doc = _doc()
    parts = _flatten_ir_doc_text(doc)
    field_names = {name for name, _ in parts}
    assert "title" in field_names
    assert "summary" in field_names
    assert "scope" in field_names
    assert "comms_draft" in field_names
    assert any(n.startswith("timeline[") for n in field_names)
    assert any(n.startswith("indicators[") for n in field_names)
    assert any(n.startswith("action_items[") for n in field_names)
