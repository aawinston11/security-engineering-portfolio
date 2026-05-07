"""CLI entry points: `make run` and `make eval`."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from .agent import triage_alert
from .eval import run_eval
from .llm import get_backend
from .mcp_client import mcp_session
from .schema import Alert

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


async def _run_one(alert_id: str | None = None) -> None:
    rows = [
        Alert(**json.loads(line))
        for line in (DATA_DIR / "alerts.jsonl").read_text().splitlines()
        if line.strip()
    ]
    if alert_id:
        rows = [a for a in rows if a.alert_id == alert_id]
        if not rows:
            sys.exit(f"alert_id {alert_id!r} not found")
    alert = rows[0]
    print(f"Triaging {alert.alert_id} — {alert.name}")
    print(f"  host={alert.host} user={alert.user} raw_severity={alert.raw_severity}\n")

    llm = get_backend()
    print(f"Backend: {llm.name} / {llm.model}\n")

    async with mcp_session() as session:
        result = await triage_alert(alert, llm=llm, session=session)

    if result.decision:
        d = result.decision
        print("=== Decision ===")
        print(f"  verdict:    {d.verdict}")
        print(f"  severity:   {d.severity}")
        print(f"  confidence: {d.confidence}")
        print(f"  techniques: {', '.join(d.mitre_techniques) or '(none)'}")
        print(f"\n  reasoning: {d.reasoning}")
        print("\n  recommended actions:")
        for a in d.recommended_actions:
            print(f"    - {a}")
    else:
        print("=== No decision produced ===")
        print(f"  error: {result.error}")
        if result.raw_text:
            print(f"  raw text: {result.raw_text[:500]}")

    print(
        f"\n  ({result.tool_calls} tool calls, {result.turns} turns, "
        f"{result.latency_seconds:.2f}s, "
        f"in={result.input_tokens} out={result.output_tokens} "
        f"cache_r={result.cache_read_input_tokens} cache_w={result.cache_creation_input_tokens})"
    )


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: cli.py {run [alert_id] | eval}")
    cmd = sys.argv[1]
    if cmd == "run":
        alert_id = sys.argv[2] if len(sys.argv) > 2 else None
        asyncio.run(_run_one(alert_id))
    elif cmd == "eval":
        asyncio.run(run_eval())
    else:
        sys.exit(f"unknown command: {cmd!r}")


if __name__ == "__main__":
    main()
