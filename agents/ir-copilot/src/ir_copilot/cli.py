"""CLI: `make run`, `make eval`, `make redteam`."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from .agent import generate_ir_doc  # noqa: E402
from .eval import run_eval, run_redteam  # noqa: E402
from .llm import get_backend  # noqa: E402
from .schema import Transcript  # noqa: E402

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

USAGE = """\
usage: python -m ir_copilot.cli {run [transcript_id] | eval | redteam}

Commands:
  run [transcript_id]  Generate one IR doc (default: first in dataset)
  eval                 Score 5 happy-path transcripts (schema, status, severity)
  redteam              Run 3 prompt-injection cases; assert defenses hold

Environment:
  LLM_BACKEND              anthropic (default) | openai | ollama (stub)
  ANTHROPIC_API_KEY        required when LLM_BACKEND=anthropic
  ANTHROPIC_MODEL          override model (default: claude-sonnet-4-6)
  OPENAI_API_KEY           required when LLM_BACKEND=openai
  OPENAI_MODEL             override model (default: gpt-5-mini)
  OPENAI_REASONING_EFFORT  default: medium (set empty to omit)

Examples:
  uv run python -m ir_copilot.cli run
  uv run python -m ir_copilot.cli run INC-002
  uv run python -m ir_copilot.cli redteam
  LLM_BACKEND=openai uv run python -m ir_copilot.cli eval
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


async def _run_one(transcript_id: str | None = None) -> None:
    rows = [
        Transcript(**json.loads(line))
        for line in (DATA_DIR / "transcripts.jsonl").read_text().splitlines()
        if line.strip()
    ]
    if transcript_id:
        all_ids = [t.transcript_id for t in rows]
        if transcript_id not in all_ids:
            preview = ", ".join(all_ids[:5]) + (", ..." if len(all_ids) > 5 else "")
            sys.exit(
                f"transcript_id {transcript_id!r} not found. Valid IDs: {preview}\n"
                f"Full list: data/transcripts.jsonl"
            )
        rows = [t for t in rows if t.transcript_id == transcript_id]
    transcript = rows[0]
    print(f"Generating IR doc for {transcript.transcript_id} ({transcript.channel})")
    print(f"  {len(transcript.messages)} transcript messages\n")

    llm = get_backend()
    print(f"Backend: {llm.name} / {llm.model}\n")

    result = await generate_ir_doc(transcript, llm=llm)

    if result.ir_doc:
        d = result.ir_doc
        print("=== IR Doc ===")
        print(f"  title:    {d.title}")
        print(f"  status:   {d.status}")
        print(f"  severity: {d.severity}")
        print(f"\n  summary: {d.summary}")
        print(f"\n  scope: {d.scope}")
        print(f"\n  timeline ({len(d.timeline)} events):")
        for ev in d.timeline:
            print(f"    [{ev.timestamp}] {ev.actor}: {ev.description}")
        print(f"\n  indicators ({len(d.indicators)}):")
        for ind in d.indicators:
            print(f"    {ind.type}: {ind.value} — {ind.context}")
        print(f"\n  action items ({len(d.action_items)}):")
        for a in d.action_items:
            print(f"    [{a.priority}] {a.description} (owner: {a.owner_role})")
        print(f"\n  comms draft:\n    {d.comms_draft}")
    else:
        print("=== No IR doc produced ===")
        print(f"  error: {result.error}")
        if result.raw_text:
            print(f"  raw text (first 500 chars): {result.raw_text[:500]}")

    u = result.usage
    print(
        f"\n  ({result.latency_seconds:.2f}s, "
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
        tid = args[1] if len(args) > 1 else None
        asyncio.run(_run_one(tid))
    elif cmd == "eval":
        _check_backend_and_key()
        asyncio.run(run_eval())
    elif cmd == "redteam":
        _check_backend_and_key()
        asyncio.run(run_redteam())
    else:
        print(f"unknown command: {cmd!r}\n\n{USAGE}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
