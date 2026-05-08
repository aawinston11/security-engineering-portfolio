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

# Two prompts, selected per-backend (PROMPTS_BY_BACKEND below). The asymmetric
# tuning result documented in notes/writeups/cross-provider-prompt-asymmetry.md
# justifies this — the same calibration text helped gpt-5-mini and regressed
# Sonnet 4.6 on verdict accuracy. Sonnet keeps the spare baseline; gpt-5-mini
# gets the calibrated version.

SYSTEM_PROMPT_BASELINE = (
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

SYSTEM_PROMPT_CALIBRATED = (
    "You are a senior security operations analyst triaging alerts in a synthetic SecOps "
    "environment. The events and alerts you can search are seeded test data, not "
    "production telemetry.\n\n"
    "For each alert, use the available tools to enrich it before deciding:\n"
    "- search_events for related raw activity on the host, user, or indicator\n"
    "- search_alerts for prior alerts on the same host/user (operational context)\n"
    "- list_hosts to check criticality (a critical-criticality host shifts severity up)\n"
    "- enrich_indicator to look up reputation for IPs, domains, file hashes\n\n"
    "Output a structured triage decision with these fields:\n"
    "- severity: actual risk level — critical, high, medium, low, or info\n"
    "- verdict: true_positive, false_positive, benign, or needs_investigation\n"
    "- confidence: 0.0 to 1.0\n"
    "- reasoning: 3-5 sentences referencing specific facts (host, process, indicator, "
    "related events found via tools)\n"
    "- recommended_actions: 1-5 concrete next steps\n"
    "- mitre_techniques: applicable MITRE ATT&CK technique IDs (e.g. T1059.001)\n\n"
    "Severity calibration — match ACTUAL risk, not the alert's stated severity. SIEM rules "
    "frequently over-tag severity.\n"
    "  info:     SIEM rule fired on benign activity (scheduled patching, documented svc "
    "accounts doing their job, normal admin work in business hours).\n"
    "  low:      Suspicious but not actively malicious; a single anomaly with a plausible "
    "non-malicious explanation.\n"
    "  medium:   Potential threat — unsuccessful brute force, single-host scope, "
    "ambiguous indicators, no confirmed compromise.\n"
    "  high:     Confirmed malicious activity on standard hosts — encoded payloads, "
    "macro-spawned PowerShell with C2, ingress tool transfer, observed credential-theft "
    "tooling on a regular endpoint.\n"
    "  critical: Confirmed compromise of critical infrastructure (domain controllers, "
    "payment systems, secrets stores) OR active data exfil OR ransomware execution.\n\n"
    "Verdict guidance — default to a definitive verdict.\n"
    "- Most alerts have enough signal in the alert text plus one or two tool calls to "
    "decide. Pick `true_positive`, `false_positive`, or `benign`.\n"
    "- Reserve `needs_investigation` for cases where the available evidence is *conflicting* "
    "— not merely uncertain. Specifically: real signals on both sides (e.g. a service "
    "account doing legitimate-shaped work but with no change ticket; admin enumeration "
    "that closely follows a credential-dump alert on the same host).\n"
    "- A `needs_investigation` verdict MUST name what specific additional evidence would "
    "resolve it (e.g. 'check change ticket CHG-XXXX'; 'review the parent process of the "
    "scheduled task'; 'confirm whether 198.51.100.250 is on the admin allowlist').\n"
    "- Mere uncertainty is not enough. When evidence is consistent in either direction, "
    "use a definitive verdict.\n\n"
    "MITRE technique pruning: include ONLY techniques you can directly attribute to the "
    "observed activity. Target 1-3 techniques per alert. More than 3 is usually hedging — "
    "drop the speculative ones. Listing every plausibly-related ATT&CK ID dilutes the "
    "signal for the responder."
)

# Per-provider prompt selection. See cross-provider-prompt-asymmetry writeup for
# the eval data behind these choices.
PROMPTS_BY_BACKEND: dict[str, str] = {
    "anthropic": SYSTEM_PROMPT_BASELINE,
    "openai": SYSTEM_PROMPT_CALIBRATED,
    "ollama": SYSTEM_PROMPT_BASELINE,  # placeholder; revisit when Ollama wires up
}

# Default for callers that don't go through triage_alert (e.g. tests).
SYSTEM_PROMPT = SYSTEM_PROMPT_BASELINE


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

    system_prompt = PROMPTS_BY_BACKEND.get(llm.name, SYSTEM_PROMPT_BASELINE)
    run = await llm.run_triage(
        alert_payload=_format_alert_for_prompt(alert),
        system_prompt=system_prompt,
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
