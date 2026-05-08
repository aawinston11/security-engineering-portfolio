"""Agent orchestrator: build tools from MCP, delegate the loop to the chosen backend.

The actual agent loop lives in each LLM backend (Anthropic/OpenAI/Ollama) since
the providers' tool-calling shapes don't translate cleanly through a single
abstraction. This module is the thin glue: it lists MCP tools, translates them
to the backend-agnostic GenericTool, and provides an async tool-execution
callback that the backend invokes when the model wants to call a tool.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass

from mcp.client.session import ClientSession

from .llm import GenericTool, LLMBackend, Usage
from .mcp_client import call_tool, mcp_tool_to_anthropic
from .schema import TRIAGE_OUTPUT_SCHEMA, Alert, TriageDecision

SYSTEM_PROMPT = (
    "You are a senior security operations analyst triaging alerts in a synthetic SecOps "
    "environment. The events you can search are seeded test data, not production telemetry.\n\n"
    "For each alert: use the available tools to enrich it (search_events for related "
    "activity, host context, indicator activity, temporal neighbors), then make a triage "
    "decision.\n\n"
    "Output a structured triage decision with these fields:\n"
    "- severity: actual risk level — critical, high, medium, low, or info\n"
    "- verdict: true_positive, false_positive, benign, or needs_investigation\n"
    "- confidence: 0.0 to 1.0\n"
    "- reasoning: 3-5 sentences referencing specific facts (host, process, indicator, "
    "related events found via tools)\n"
    "- recommended_actions: 1-5 concrete next steps\n"
    "- mitre_techniques: applicable MITRE ATT&CK technique IDs (e.g. T1059.001)\n\n"
    "Use tools before deciding when in doubt — do not guess from the alert text alone. "
    "Match severity to actual risk, not the alert's stated severity. A verdict of "
    "needs_investigation requires you to identify specifically what is ambiguous and "
    "what would resolve it.\n\n"
    "# Note on prompt iteration\n"
    "# A more elaborate version of this prompt with explicit severity-calibration tables "
    "# and ambiguity-case guidance was tested. It improved OpenAI gpt-5-mini scores "
    "# (severity +20pt, MITRE IoU +0.17) but regressed Anthropic Sonnet 4.6 "
    "# (verdict -27pt; model began over-using needs_investigation). See the README for "
    "# the full asymmetric-tuning result. Provider-specific prompts are an open "
    "# direction for the next iteration."
)


@dataclass
class TriageResult:
    decision: TriageDecision | None
    schema_valid: bool
    tool_calls: int
    turns: int
    latency_seconds: float
    error: str | None
    raw_text: str | None
    usage: Usage


def _format_alert_for_prompt(alert: Alert) -> str:
    return "Triage the following alert.\n\n```json\n" + json.dumps(alert.model_dump(), indent=2) + "\n```"


async def triage_alert(
    alert: Alert,
    *,
    llm: LLMBackend,
    session: ClientSession,
) -> TriageResult:
    started = time.monotonic()

    tools_resp = await session.list_tools()
    generic_tools = [
        GenericTool(
            name=t.name,
            description=mcp_tool_to_anthropic(t)["description"],
            input_schema=mcp_tool_to_anthropic(t)["input_schema"],
        )
        for t in tools_resp.tools
    ]

    async def _execute_tool(name: str, args: dict) -> str:
        return await call_tool(session, name, args)

    run = await llm.run_triage(
        alert_payload=_format_alert_for_prompt(alert),
        system_prompt=SYSTEM_PROMPT,
        tools=generic_tools,
        output_schema=TRIAGE_OUTPUT_SCHEMA,
        execute_tool=_execute_tool,
    )

    return TriageResult(
        decision=run.decision,
        schema_valid=run.schema_valid,
        tool_calls=run.tool_calls,
        turns=run.turns,
        latency_seconds=time.monotonic() - started,
        error=run.error,
        raw_text=run.raw_text,
        usage=run.usage,
    )
