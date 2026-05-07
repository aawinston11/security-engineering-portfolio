"""MCP -> Anthropic tool conversion. No LLM, no live MCP."""
from __future__ import annotations

from types import SimpleNamespace

from alert_triage.mcp_client import mcp_tool_to_anthropic


def test_mcp_tool_to_anthropic_basic() -> None:
    schema = {
        "type": "object",
        "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}},
        "required": ["query"],
    }
    mcp_tool = SimpleNamespace(
        name="search_events",
        description="Search the SIEM for events.\nMore detail.",
        inputSchema=schema,
    )
    out = mcp_tool_to_anthropic(mcp_tool)
    assert out == {
        "name": "search_events",
        "description": "Search the SIEM for events.\nMore detail.",
        "input_schema": schema,
    }


def test_mcp_tool_to_anthropic_handles_missing_schema() -> None:
    mcp_tool = SimpleNamespace(name="ping", description=None, inputSchema=None)
    out = mcp_tool_to_anthropic(mcp_tool)
    assert out["name"] == "ping"
    assert out["description"] == ""
    assert out["input_schema"] == {"type": "object", "properties": {}}
