"""Schemas for transcripts, IR docs, ground truth, and red-team expectations.

The IRDoc schema is also rendered as JSON Schema for the API's structured-output
constraint (Anthropic `output_config.format` / OpenAI `response_format`). The two
are kept aligned by hand because Pydantic-generated schemas may include
constraints (e.g. minLength) that aren't supported by the API-side enforcement.
Pydantic enforces strict constraints on the client side after parse.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

Severity = Literal["critical", "high", "medium", "low", "info"]
Status = Literal["active", "investigating", "contained", "resolved", "false_alarm"]
Priority = Literal["critical", "high", "medium", "low"]


class TimelineEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: str
    actor: str
    description: str


class Indicator(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    value: str
    context: str


class ActionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: Priority
    description: str
    owner_role: str


class IRDoc(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    summary: str
    severity: Severity
    status: Status
    timeline: list[TimelineEvent]
    scope: str
    indicators: list[Indicator]
    action_items: list[ActionItem]
    comms_draft: str


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ts: str
    user: str
    text: str


class Transcript(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transcript_id: str
    channel: str
    messages: list[Message]
    # Red-team transcripts include this; happy-path ones don't.
    injection_summary: str | None = None


class GroundTruth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transcript_id: str
    expected_severity: Severity
    expected_status: Status
    min_indicators: int
    min_action_items: int
    notes: str


class RedTeamExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transcript_id: str
    must_not_have_status: list[str]
    must_not_have_severity: list[str]
    must_not_appear_in_any_field: list[str]
    notes: str


# Hand-written JSON Schema for API-side structured output enforcement.
IR_DOC_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "severity": {"type": "string", "enum": ["critical", "high", "medium", "low", "info"]},
        "status": {
            "type": "string",
            "enum": ["active", "investigating", "contained", "resolved", "false_alarm"],
        },
        "timeline": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "timestamp": {"type": "string"},
                    "actor": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["timestamp", "actor", "description"],
                "additionalProperties": False,
            },
        },
        "scope": {"type": "string"},
        "indicators": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "value": {"type": "string"},
                    "context": {"type": "string"},
                },
                "required": ["type", "value", "context"],
                "additionalProperties": False,
            },
        },
        "action_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "priority": {
                        "type": "string",
                        "enum": ["critical", "high", "medium", "low"],
                    },
                    "description": {"type": "string"},
                    "owner_role": {"type": "string"},
                },
                "required": ["priority", "description", "owner_role"],
                "additionalProperties": False,
            },
        },
        "comms_draft": {"type": "string"},
    },
    "required": [
        "title",
        "summary",
        "severity",
        "status",
        "timeline",
        "scope",
        "indicators",
        "action_items",
        "comms_draft",
    ],
    "additionalProperties": False,
}
