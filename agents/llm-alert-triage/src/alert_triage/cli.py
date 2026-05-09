"""CLI entry points: `make run` and `make eval`."""
from __future__ import annotations

import asyncio
import json
import os
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

USAGE = """\
usage: python -m alert_triage.cli {run [alert_id] | eval}

Commands:
  run [alert_id]   Triage one alert (default: first in dataset)
  eval             Run the eval harness on all 15 labeled alerts

Environment:
  LLM_BACKEND              anthropic (default) | openai | ollama (stub)
  ANTHROPIC_API_KEY        required when LLM_BACKEND=anthropic
  ANTHROPIC_MODEL          override model (default: claude-sonnet-4-6)
  OPENAI_API_KEY           required when LLM_BACKEND=openai
  OPENAI_MODEL             override model (default: gpt-5-mini)
  OPENAI_REASONING_EFFORT  default: medium (set empty to omit)

Examples:
  uv run python -m alert_triage.cli run
  uv run python -m alert_triage.cli run ALERT-007
  LLM_BACKEND=openai uv run python -m alert_triage.cli eval
"""

VALID_BACKENDS = ("anthropic", "openai", "ollama")
KEY_BY_BACKEND = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}


def _check_backend_and_key() -> None:
    """Validate LLM_BACKEND and the required API key before kicking off async work.
    Surfaces a single fixable line instead of a Python traceback or raw SDK error."""
    backend = os.environ.get("LLM_BACKEND", "anthropic").lower()
    if backend not in VALID_BACKENDS:
        sys.exit(
            f"LLM_BACKEND={backend!r} is invalid. "
            f"Valid: {', '.join(VALID_BACKENDS)}."
        )
    required = KEY_BY_BACKEND.get(backend)
    if required and not os.environ.get(required):
        sys.exit(
            f"{required} not set for LLM_BACKEND={backend}. Either:\n"
            f"  cp .env.example .env && $EDITOR .env   (at the repo root)\n"
            f"  export {required}=<your-key>           (in the shell)\n"
            f"\n.env is gitignored. Never commit it."
        )


async def _run_one(alert_id: str | None = None) -> None:
    rows = [
        Alert(**json.loads(line))
        for line in (DATA_DIR / "alerts.jsonl").read_text().splitlines()
        if line.strip()
    ]
    if alert_id:
        all_ids = [a.alert_id for a in rows]
        if alert_id not in all_ids:
            preview = ", ".join(all_ids[:5]) + (", ..." if len(all_ids) > 5 else "")
            sys.exit(
                f"alert_id {alert_id!r} not found. Valid IDs: {preview}\n"
                f"Full list: data/alerts.jsonl"
            )
        rows = [a for a in rows if a.alert_id == alert_id]
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
    args = sys.argv[1:]
    if not args:
        print(USAGE, file=sys.stderr)
        sys.exit(2)
    if args[0] in ("--help", "-h", "help"):
        print(USAGE)
        sys.exit(0)
    cmd = args[0]
    if cmd == "run":
        _check_backend_and_key()
        alert_id = args[1] if len(args) > 1 else None
        asyncio.run(_run_one(alert_id))
    elif cmd == "eval":
        _check_backend_and_key()
        asyncio.run(run_eval())
    else:
        print(f"unknown command: {cmd!r}\n\n{USAGE}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
