"""Synthetic SIEM mock — deterministic backend for the MCP server's tools.

Loads events, alerts, hosts, and indicators from `data/*.jsonl` at startup.
Provides read-only endpoints with API-key authentication. Designed to be
deterministic so eval results are reproducible.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel

DATA_DIR = Path(os.environ.get("SIEM_DATA_DIR", "data"))
EVENTS_PATH = Path(os.environ.get("SIEM_DATA_PATH", DATA_DIR / "events.jsonl"))
ALERTS_PATH = DATA_DIR / "alerts.jsonl"
HOSTS_PATH = DATA_DIR / "hosts.jsonl"
INDICATORS_PATH = DATA_DIR / "indicators.jsonl"

API_KEY = os.environ.get("SIEM_API_KEY", "dev-readonly-key")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


_EVENTS: list[dict[str, Any]] = _load_jsonl(EVENTS_PATH)
_ALERTS: list[dict[str, Any]] = _load_jsonl(ALERTS_PATH)
_HOSTS: list[dict[str, Any]] = _load_jsonl(HOSTS_PATH)
_INDICATORS: dict[str, dict[str, Any]] = {
    ind["value"]: ind for ind in _load_jsonl(INDICATORS_PATH)
}


def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> str:
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing X-API-Key",
        )
    return x_api_key


def _parse_query(q: str) -> dict[str, str]:
    """Naive `key=value` query parser. Multiple terms are AND-ed."""
    filters: dict[str, str] = {}
    for term in q.split():
        if "=" in term:
            k, v = term.split("=", 1)
            filters[k.strip()] = v.strip()
    return filters


def _matches(record: dict[str, Any], filters: dict[str, str]) -> bool:
    return all(str(record.get(k)) == v for k, v in filters.items())


app = FastAPI(title="Synthetic SIEM Mock", version="0.2.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "events_loaded": str(len(_EVENTS)),
        "alerts_loaded": str(len(_ALERTS)),
        "hosts_loaded": str(len(_HOSTS)),
        "indicators_loaded": str(len(_INDICATORS)),
    }


# ---------- events ----------

class EventSearchResponse(BaseModel):
    matched: int
    events: list[dict[str, Any]]


@app.get(
    "/events/search",
    response_model=EventSearchResponse,
    dependencies=[Depends(require_api_key)],
)
def search_events(query: str = "", limit: int = 50) -> EventSearchResponse:
    """Naive `key=value` query parser. Multiple terms are AND-ed.

    Examples:
      query='process.name=powershell.exe host=finance03'
      query='mitre_technique=T1059.001'
      query=''  (returns all events)

    Sorted by timestamp ascending. Deterministic.
    """
    filters = _parse_query(query)
    matches = [ev for ev in _EVENTS if _matches(ev, filters)]
    matches.sort(key=lambda e: e.get("timestamp", ""))
    bounded = matches[: max(0, limit)]
    return EventSearchResponse(matched=len(matches), events=bounded)


# ---------- alerts ----------

class AlertSearchResponse(BaseModel):
    matched: int
    alerts: list[dict[str, Any]]


@app.get("/alerts/search", response_model=AlertSearchResponse,
         dependencies=[Depends(require_api_key)])
def search_alerts(query: str = "", limit: int = 20) -> AlertSearchResponse:
    """Search the alert history (closed + open). Same query language as events."""
    filters = _parse_query(query)
    matches = [a for a in _ALERTS if _matches(a, filters)]
    matches.sort(key=lambda a: a.get("timestamp", ""))
    bounded = matches[: max(0, limit)]
    return AlertSearchResponse(matched=len(matches), alerts=bounded)


@app.get("/alerts/{alert_id}", dependencies=[Depends(require_api_key)])
def get_alert(alert_id: str) -> dict[str, Any]:
    """Fetch a single alert by ID. 404 if not found."""
    for a in _ALERTS:
        if a.get("alert_id") == alert_id:
            return a
    raise HTTPException(status_code=404, detail=f"alert {alert_id!r} not found")


# ---------- hosts ----------

class HostListResponse(BaseModel):
    matched: int
    hosts: list[dict[str, Any]]


@app.get("/hosts", response_model=HostListResponse, dependencies=[Depends(require_api_key)])
def list_hosts(query: str = "", limit: int = 50) -> HostListResponse:
    """List hosts in the asset inventory. Same query language."""
    filters = _parse_query(query)
    matches = [h for h in _HOSTS if _matches(h, filters)]
    bounded = matches[: max(0, limit)]
    return HostListResponse(matched=len(matches), hosts=bounded)


# ---------- indicators ----------

@app.get("/indicators/{indicator_value:path}", dependencies=[Depends(require_api_key)])
def enrich_indicator(indicator_value: str) -> dict[str, Any]:
    """Threat-intel enrichment for an IP, domain, or hash.
    Returns `{known: false, reputation: "unknown"}` for unknown indicators
    (that's the right product behavior — absence of TI is not an error)."""
    ind = _INDICATORS.get(indicator_value)
    if not ind:
        return {
            "value": indicator_value,
            "known": False,
            "reputation": "unknown",
            "tags": [],
            "related": [],
        }
    return {**ind, "known": True}
