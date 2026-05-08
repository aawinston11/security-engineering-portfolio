"""MCP Security Tooling Server.

Exposes a synthetic SIEM/EDR API as MCP tools to LLM agents over stdio.
Five read tools today; containment-class tools (e.g. `quarantine_host`) are
the next surface and will require an `act:contain` scope and a separate API
key. Every tool invocation appends an entry to the HMAC-chained audit log.
"""
from __future__ import annotations

import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from .audit import AuditLog

SIEM_BASE_URL = os.environ.get("SIEM_BASE_URL", "http://localhost:8765")
SIEM_API_KEY = os.environ.get("SIEM_API_KEY", "dev-readonly-key")
AUDIT_PATH = os.environ.get("AUDIT_LOG_PATH", "audit/audit.jsonl")
AUDIT_HMAC_KEY = os.environ.get("AUDIT_HMAC_KEY", "dev-only-not-secret").encode()

mcp = FastMCP("security-tooling")
audit = AuditLog(path=AUDIT_PATH, hmac_key=AUDIT_HMAC_KEY)


def _siem_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    with httpx.Client(timeout=5.0) as client:
        resp = client.get(
            f"{SIEM_BASE_URL}{path}",
            params=params,
            headers={"X-API-Key": SIEM_API_KEY},
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------

@mcp.tool()
def search_events(query: str = "", limit: int = 50) -> dict:
    """Search the SIEM for raw events matching a key=value query.

    Examples:
      query='process.name=powershell.exe' limit=10
      query='host=finance03 mitre_technique=T1059.001'
      query=''

    Returns: dict with `matched` (total) and `events` (list, capped at limit),
    sorted by timestamp ascending. Read-only; requires `read:events` scope.
    """
    result = _siem_get("/events/search", {"query": query, "limit": limit})
    audit.append(
        tool="search_events",
        args={"query": query, "limit": limit},
        result_summary={"matched": result["matched"], "returned": len(result["events"])},
    )
    return result


@mcp.tool()
def search_alerts(query: str = "", limit: int = 20) -> dict:
    """Search the alert history (closed + open) using the same key=value query
    language as `search_events`. Useful for surfacing related historical alerts
    on the same host/user during triage.

    Examples:
      query='host=finance03'
      query='user=jsmith verdict=true_positive'
      query='severity=critical'

    Read-only; requires `read:alerts` scope.
    """
    result = _siem_get("/alerts/search", {"query": query, "limit": limit})
    audit.append(
        tool="search_alerts",
        args={"query": query, "limit": limit},
        result_summary={"matched": result["matched"], "returned": len(result["alerts"])},
    )
    return result


@mcp.tool()
def get_alert(alert_id: str) -> dict:
    """Fetch a single alert by ID from the alert history.

    Returns the alert JSON if found, or `{found: false}` if the ID is unknown.
    Read-only; requires `read:alerts` scope.
    """
    with httpx.Client(timeout=5.0) as client:
        resp = client.get(
            f"{SIEM_BASE_URL}/alerts/{alert_id}",
            headers={"X-API-Key": SIEM_API_KEY},
        )
    if resp.status_code == 404:
        audit.append(tool="get_alert", args={"alert_id": alert_id},
                     result_summary={"found": False})
        return {"alert_id": alert_id, "found": False}
    resp.raise_for_status()
    result = resp.json()
    audit.append(tool="get_alert", args={"alert_id": alert_id},
                 result_summary={"found": True})
    return result


@mcp.tool()
def list_hosts(query: str = "", limit: int = 50) -> dict:
    """List hosts in the asset inventory. Returns hostname, IP, OS, owner,
    department, criticality, and tags.

    Examples:
      query='criticality=critical'
      query='department=finance'
      query=''  (returns all hosts)

    Read-only; requires `read:assets` scope.
    """
    result = _siem_get("/hosts", {"query": query, "limit": limit})
    audit.append(
        tool="list_hosts",
        args={"query": query, "limit": limit},
        result_summary={"matched": result["matched"], "returned": len(result["hosts"])},
    )
    return result


@mcp.tool()
def enrich_indicator(indicator: str) -> dict:
    """Look up threat-intel enrichment for an indicator (IP, domain, file hash).

    Returns reputation (malicious / suspicious / unknown), first_seen,
    last_seen, tags, and related indicators. For unknown indicators, returns
    `{known: false, reputation: "unknown"}` — the absence of TI is informative,
    not an error.

    Examples:
      indicator='malicious.example.invalid'
      indicator='198.51.100.7'

    Read-only; requires `read:indicators` scope.
    """
    result = _siem_get(f"/indicators/{indicator}")
    audit.append(
        tool="enrich_indicator",
        args={"indicator": indicator},
        result_summary={
            "known": result.get("known", False),
            "reputation": result.get("reputation", "unknown"),
        },
    )
    return result


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
