"""Test fixtures.

The SIEM mock is expected to be running already (via `make siem-up` or `docker
compose up siem-mock`). Tests fail fast with a clear message if it's not.
"""
from __future__ import annotations

import os
import time

import httpx
import pytest

SIEM_URL = os.environ.get("SIEM_BASE_URL", "http://localhost:8765")
SIEM_KEY = os.environ.get("SIEM_API_KEY", "dev-readonly-key")


@pytest.fixture(scope="session", autouse=True)
def ensure_siem_up() -> None:
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            r = httpx.get(f"{SIEM_URL}/health", timeout=1.0)
            if r.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    pytest.fail(
        f"SIEM mock not reachable at {SIEM_URL}. "
        f"Run `make siem-up` (or `docker compose up -d siem-mock`) first."
    )


@pytest.fixture
def siem_url() -> str:
    return SIEM_URL


@pytest.fixture
def siem_key() -> str:
    return SIEM_KEY
