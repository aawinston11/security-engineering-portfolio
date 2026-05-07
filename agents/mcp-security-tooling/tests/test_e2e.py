"""End-to-end tests: SIEM mock direct, plus audit-log integrity."""
from __future__ import annotations

import json
from pathlib import Path

import httpx

from mcp_security_tooling.audit import AuditLog


# ---------- SIEM mock (HTTP layer) ----------

def test_siem_health(siem_url: str) -> None:
    r = httpx.get(f"{siem_url}/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert int(body["events_loaded"]) >= 1


def test_siem_search_requires_auth(siem_url: str) -> None:
    r = httpx.get(f"{siem_url}/events/search")
    assert r.status_code == 401


def test_siem_search_rejects_bad_key(siem_url: str) -> None:
    r = httpx.get(
        f"{siem_url}/events/search",
        headers={"X-API-Key": "wrong"},
    )
    assert r.status_code == 401


def test_siem_search_returns_events(siem_url: str, siem_key: str) -> None:
    r = httpx.get(
        f"{siem_url}/events/search",
        params={"query": "", "limit": 50},
        headers={"X-API-Key": siem_key},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["matched"] >= 1
    assert len(body["events"]) <= 50


def test_siem_search_filters_correctly(siem_url: str, siem_key: str) -> None:
    r = httpx.get(
        f"{siem_url}/events/search",
        params={"query": "mitre_technique=T1059.001", "limit": 10},
        headers={"X-API-Key": siem_key},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["matched"] >= 1
    for ev in body["events"]:
        assert ev["mitre_technique"] == "T1059.001"


def test_siem_search_is_deterministic(siem_url: str, siem_key: str) -> None:
    """Same query twice returns identical results (eval reproducibility)."""
    params = {"query": "host=finance03", "limit": 50}
    headers = {"X-API-Key": siem_key}
    r1 = httpx.get(f"{siem_url}/events/search", params=params, headers=headers).json()
    r2 = httpx.get(f"{siem_url}/events/search", params=params, headers=headers).json()
    assert r1 == r2


# ---------- Audit log (HMAC chain) ----------

def test_audit_log_writes_and_verifies(tmp_path: Path) -> None:
    log = AuditLog(path=tmp_path / "audit.jsonl", hmac_key=b"test-key")
    log.append(tool="search_events", args={"q": "a"}, result_summary={"n": 1})
    log.append(tool="search_events", args={"q": "b"}, result_summary={"n": 2})
    log.append(tool="search_events", args={"q": "c"}, result_summary={"n": 3})
    assert log.verify() is True


def test_audit_log_detects_tampering(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path=path, hmac_key=b"test-key")
    log.append(tool="search_events", args={"q": "a"}, result_summary={"n": 1})
    log.append(tool="search_events", args={"q": "b"}, result_summary={"n": 2})
    log.append(tool="search_events", args={"q": "c"}, result_summary={"n": 3})

    lines = path.read_text().splitlines()
    entry = json.loads(lines[1])
    entry["tool"] = "tampered"
    lines[1] = json.dumps(entry)
    path.write_text("\n".join(lines) + "\n")

    log2 = AuditLog(path=path, hmac_key=b"test-key")
    assert log2.verify() is False


def test_audit_log_detects_wrong_key(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path=path, hmac_key=b"correct-key")
    log.append(tool="search_events", args={"q": "a"}, result_summary={"n": 1})

    log_wrong = AuditLog(path=path, hmac_key=b"wrong-key")
    assert log_wrong.verify() is False
