"""Tamper-evident audit log.

Each entry HMAC-chains the previous entry's signature, so any single-line edit
breaks verification. The result is an append-only record of every tool
invocation that's cheap to write and easy to verify.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time
from pathlib import Path
from typing import Any


class AuditLog:
    def __init__(self, path: str | os.PathLike, hmac_key: bytes) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._key = hmac_key
        self._lock = threading.Lock()
        self._prev = self._load_last_signature()

    def _load_last_signature(self) -> str:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return ""
        last = self.path.read_text().splitlines()[-1]
        try:
            return json.loads(last).get("signature", "")
        except json.JSONDecodeError:
            return ""

    def append(
        self,
        *,
        tool: str,
        args: dict[str, Any],
        result_summary: dict[str, Any],
    ) -> str:
        with self._lock:
            payload = {
                "ts": time.time(),
                "tool": tool,
                "args_hash": _sha256(args),
                "result_hash": _sha256(result_summary),
                "prev_signature": self._prev,
            }
            sig = self._sign(payload)
            entry = {**payload, "signature": sig}
            with self.path.open("a") as f:
                f.write(json.dumps(entry) + "\n")
            self._prev = sig
            return sig

    def verify(self) -> bool:
        if not self.path.exists():
            return True
        prev = ""
        for line in self.path.read_text().splitlines():
            entry = json.loads(line)
            payload = {
                k: entry[k]
                for k in ("ts", "tool", "args_hash", "result_hash", "prev_signature")
            }
            if entry["signature"] != self._sign(payload, prev_override=prev):
                return False
            prev = entry["signature"]
        return True

    def _sign(self, payload: dict[str, Any], *, prev_override: str | None = None) -> str:
        prev = self._prev if prev_override is None else prev_override
        msg = (prev + json.dumps(payload, sort_keys=True)).encode()
        return hmac.new(self._key, msg, hashlib.sha256).hexdigest()


def _sha256(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()
