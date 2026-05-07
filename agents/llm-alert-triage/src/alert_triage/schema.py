"""Schemas for alerts, decisions, and ground truth.

The TriageDecision schema is also rendered as JSON Schema for the Anthropic API's
output_config.format — see TRIAGE_OUTPUT_SCHEMA below. The two are kept in sync by
hand because Pydantic's auto-generated schema includes constraints (string length,
numeric ranges) that aren't supported in output_config. Pydantic enforces the
strict constraints on the client side after parse.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

Severity = Literal["critical", "high", "medium", "low", "info"]
Verdict = Literal["true_positive", "false_positive", "benign", "needs_investigation"]


class TriageDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: Severity
    verdict: Verdict
    confidence: float
    reasoning: str
    recommended_actions: list[str]
    mitre_techniques: list[str]


class Alert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alert_id: str
    name: str
    description: str
    signal_summary: str
    triggering_event_id: str
    host: str
    user: str
    timestamp: str
    raw_severity: str


class GroundTruth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alert_id: str
    verdict: Verdict
    severity: Severity
    mitre_techniques: list[str]
    notes: str


# Hand-written JSON Schema for the Anthropic output_config.format constraint.
# Stays minimal — no `minimum` / `maxLength` constraints, since those aren't supported.
TRIAGE_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "severity": {
            "type": "string",
            "enum": ["critical", "high", "medium", "low", "info"],
        },
        "verdict": {
            "type": "string",
            "enum": ["true_positive", "false_positive", "benign", "needs_investigation"],
        },
        "confidence": {"type": "number"},
        "reasoning": {"type": "string"},
        "recommended_actions": {"type": "array", "items": {"type": "string"}},
        "mitre_techniques": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "severity",
        "verdict",
        "confidence",
        "reasoning",
        "recommended_actions",
        "mitre_techniques",
    ],
    "additionalProperties": False,
}
