"""MCP Security Tooling Server.

Exposes a synthetic SIEM/EDR API as MCP tools. Every invocation is recorded
in an HMAC-chained audit log. Read-only by design at this scaffold stage —
containment-class tools (`quarantine_host`, etc.) will require an `act:`
scope and a separate API key when they land.
"""
from __future__ import annotations

import os

import httpx
from mcp.server.fastmcp import FastMCP

from .audit import AuditLog

SIEM_BASE_URL = os.environ.get("SIEM_BASE_URL", "http://localhost:8765")
SIEM_API_KEY = os.environ.get("SIEM_API_KEY", "dev-readonly-key")
AUDIT_PATH = os.environ.get("AUDIT_LOG_PATH", "audit/audit.jsonl")
AUDIT_HMAC_KEY = os.environ.get("AUDIT_HMAC_KEY", "dev-only-not-secret").encode()

mcp = FastMCP("security-tooling")
audit = AuditLog(path=AUDIT_PATH, hmac_key=AUDIT_HMAC_KEY)


@mcp.tool()
def search_events(query: str = "", limit: int = 50) -> dict:
    """Search the SIEM for events matching a key=value query.

    The query is a space-separated list of `key=value` filters that are AND-ed.
    Empty query returns all events (up to limit). Results are sorted by
    timestamp ascending.

    Examples:
      query='process.name=powershell.exe' limit=10
      query='host=finance03 mitre_technique=T1059.001'
      query=''

    Returns: dict with `matched` (total matching) and `events` (list, capped at limit).
    Read-only; requires the `read:events` scope (currently the default).
    """
    with httpx.Client(timeout=5.0) as client:
        resp = client.get(
            f"{SIEM_BASE_URL}/events/search",
            params={"query": query, "limit": limit},
            headers={"X-API-Key": SIEM_API_KEY},
        )
        resp.raise_for_status()
        result = resp.json()

    audit.append(
        tool="search_events",
        args={"query": query, "limit": limit},
        result_summary={
            "matched": result["matched"],
            "returned": len(result["events"]),
        },
    )
    return result


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
