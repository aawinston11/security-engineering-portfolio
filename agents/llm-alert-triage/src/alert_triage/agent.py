"""Agent loop: read alert -> optional MCP tool calls -> Pydantic-validated decision.

Manual agentic loop instead of the SDK's tool runner so we keep explicit control
over per-step audit, cost tracking, and termination. The output_config.format
constraint guarantees the final assistant turn is a JSON object that matches
the TriageDecision schema; we still parse with Pydantic to catch the constraints
that the API-side schema can't express (e.g. confidence range).
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from mcp.client.session import ClientSession
from pydantic import ValidationError

from .llm import LLMBackend
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
    "what would resolve it."
)

# Anthropic SDK refuses non-streaming requests above ~16K. 8K is plenty for a triage
# decision (a few hundred output tokens) plus adaptive thinking headroom.
MAX_TOKENS = 8192
MAX_TURNS = 6  # safety cap: alert + a few tool round-trips + decision


@dataclass
class TriageResult:
    decision: TriageDecision | None
    schema_valid: bool
    tool_calls: int
    turns: int
    latency_seconds: float
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int
    cache_creation_input_tokens: int
    error: str | None = None
    raw_text: str | None = None


def _format_alert_for_prompt(alert: Alert) -> str:
    payload = alert.model_dump()
    return (
        "Triage the following alert.\n\n"
        f"```json\n{json.dumps(payload, indent=2)}\n```"
    )


async def triage_alert(
    alert: Alert,
    *,
    llm: LLMBackend,
    session: ClientSession,
) -> TriageResult:
    """Run the agentic loop for a single alert."""
    started = time.monotonic()

    tools_resp = await session.list_tools()
    anthropic_tools = [mcp_tool_to_anthropic(t) for t in tools_resp.tools]

    messages: list[dict[str, Any]] = [
        {"role": "user", "content": _format_alert_for_prompt(alert)},
    ]

    tool_calls = 0
    in_tok = out_tok = cache_read = cache_create = 0
    last_text: str | None = None
    error: str | None = None
    decision: TriageDecision | None = None
    schema_valid = False
    turns = 0

    for _ in range(MAX_TURNS):
        turns += 1
        try:
            resp = llm.messages_create(
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=anthropic_tools,
                thinking={"type": "adaptive"},
                output_config={
                    "effort": "medium",
                    "format": {"type": "json_schema", "schema": TRIAGE_OUTPUT_SCHEMA},
                },
                cache_control={"type": "ephemeral"},
            )
        except Exception as e:  # noqa: BLE001 — surface any API error in the result
            error = f"{type(e).__name__}: {e}"
            break

        usage = resp.usage
        in_tok += getattr(usage, "input_tokens", 0) or 0
        out_tok += getattr(usage, "output_tokens", 0) or 0
        cache_read += getattr(usage, "cache_read_input_tokens", 0) or 0
        cache_create += getattr(usage, "cache_creation_input_tokens", 0) or 0

        if resp.stop_reason == "tool_use":
            tool_use_blocks = [b for b in resp.content if b.type == "tool_use"]
            messages.append({"role": "assistant", "content": resp.content})

            tool_results = []
            for tu in tool_use_blocks:
                tool_calls += 1
                try:
                    output = await call_tool(session, tu.name, dict(tu.input))
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": output,
                    })
                except Exception as e:  # noqa: BLE001
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": f"tool error: {type(e).__name__}: {e}",
                        "is_error": True,
                    })
            messages.append({"role": "user", "content": tool_results})
            continue

        # end_turn (or any other terminal stop_reason): parse the structured output.
        text_blocks = [b.text for b in resp.content if b.type == "text"]
        last_text = "\n".join(text_blocks).strip()
        if not last_text:
            error = f"no text content in final response (stop_reason={resp.stop_reason!r})"
            break

        try:
            decision = TriageDecision.model_validate_json(last_text)
            schema_valid = True
        except ValidationError as ve:
            error = f"schema validation failed: {ve}"
        break
    else:
        error = f"max turns ({MAX_TURNS}) exceeded without final decision"

    return TriageResult(
        decision=decision,
        schema_valid=schema_valid,
        tool_calls=tool_calls,
        turns=turns,
        latency_seconds=time.monotonic() - started,
        input_tokens=in_tok,
        output_tokens=out_tok,
        cache_read_input_tokens=cache_read,
        cache_creation_input_tokens=cache_create,
        error=error,
        raw_text=last_text,
    )
