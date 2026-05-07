"""MCP client: spawns the mcp-security-tooling server as a subprocess and
exposes a session that can list and call tools.

The server lives in `agents/mcp-security-tooling/`. The default subprocess
command is `uv run --directory <mcp-dir> python -m mcp_security_tooling.server`,
which is what the demo client in that project uses too.

Override the dir with `MCP_SERVER_DIR=...`.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

DEFAULT_MCP_DIR = Path(__file__).resolve().parents[3] / "mcp-security-tooling"


def _mcp_dir() -> Path:
    override = os.environ.get("MCP_SERVER_DIR")
    return Path(override).resolve() if override else DEFAULT_MCP_DIR


@asynccontextmanager
async def mcp_session():
    """Spawn the MCP server and yield an initialized client session."""
    mcp_dir = _mcp_dir()
    if not mcp_dir.is_dir():
        raise FileNotFoundError(
            f"MCP server directory not found: {mcp_dir}. "
            "Set MCP_SERVER_DIR or check the repo layout."
        )

    params = StdioServerParameters(
        command="uv",
        args=[
            "run",
            "--directory",
            str(mcp_dir),
            "python",
            "-m",
            "mcp_security_tooling.server",
        ],
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


def mcp_tool_to_anthropic(tool: Any) -> dict[str, Any]:
    """Convert an MCP Tool object to an Anthropic tool definition."""
    schema = getattr(tool, "inputSchema", None) or {"type": "object", "properties": {}}
    return {
        "name": tool.name,
        "description": (tool.description or "").strip(),
        "input_schema": schema,
    }


async def call_tool(session: ClientSession, name: str, args: dict[str, Any]) -> str:
    """Call an MCP tool and return the concatenated text content."""
    result = await session.call_tool(name, args)
    parts: list[str] = []
    for block in result.content or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts) if parts else "(empty result)"
