"""Synthetic SIEM mock — deterministic backend for the MCP server's tools.

Loads events from `data/events.jsonl` at startup. Provides a single search endpoint
with a naive key=value query language. API-key authentication enforced; the mock
never accepts external data ingestion.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel

DATA_PATH = Path(os.environ.get("SIEM_DATA_PATH", "data/events.jsonl"))
API_KEY = os.environ.get("SIEM_API_KEY", "dev-readonly-key")


def _load_events() -> list[dict[str, Any]]:
    if not DATA_PATH.exists():
        return []
    return [json.loads(line) for line in DATA_PATH.read_text().splitlines() if line.strip()]


_EVENTS: list[dict[str, Any]] = _load_events()


def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> str:
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing X-API-Key",
        )
    return x_api_key


app = FastAPI(title="Synthetic SIEM Mock", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "events_loaded": str(len(_EVENTS))}


class SearchResponse(BaseModel):
    matched: int
    events: list[dict[str, Any]]


@app.get(
    "/events/search",
    response_model=SearchResponse,
    dependencies=[Depends(require_api_key)],
)
def search_events(query: str = "", limit: int = 50) -> SearchResponse:
    """Naive `key=value` query parser. Multiple terms are AND-ed.

    Examples:
      query='process.name=powershell.exe host=finance03'
      query='mitre_technique=T1059.001'
      query=''  (returns all events)

    Results are sorted by timestamp ascending. Determinism is intentional:
    the same `(query, limit)` returns the same response every time.
    """
    filters: dict[str, str] = {}
    for term in query.split():
        if "=" in term:
            k, v = term.split("=", 1)
            filters[k.strip()] = v.strip()

    matches = [
        ev for ev in _EVENTS
        if all(str(ev.get(k)) == v for k, v in filters.items())
    ]
    matches.sort(key=lambda e: e.get("timestamp", ""))
    bounded = matches[: max(0, limit)]
    return SearchResponse(matched=len(matches), events=bounded)
