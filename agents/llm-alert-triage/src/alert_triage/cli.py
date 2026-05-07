"""CLI entry points: `make run` and `make eval`."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load env vars from a .env file. find_dotenv (called by load_dotenv() with no args)
# walks up from cwd, so the same .env at the repo root works whether you run from
# the project dir or anywhere underneath. Existing shell exports take precedence
# (override=False by default).
load_dotenv()

from .agent import triage_alert  # noqa: E402  — env must be loaded before backend selection
from .eval import run_eval  # noqa: E402
from .llm import get_backend  # noqa: E402
from .mcp_client import mcp_session  # noqa: E402
from .schema import Alert  # noqa: E402

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

    u = result.usage
    print(
        f"\n  ({result.tool_calls} tool calls, {result.turns} turns, "
        f"{result.latency_seconds:.2f}s, "
        f"in={u.input_tokens} out={u.output_tokens} "
        f"cached={u.cached_tokens} reasoning={u.reasoning_tokens} "
        f"cache_w={u.cache_creation_tokens})"
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
