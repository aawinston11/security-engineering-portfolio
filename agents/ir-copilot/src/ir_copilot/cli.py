"""CLI: `make run`, `make eval`, `make redteam`."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from .agent import generate_ir_doc  # noqa: E402
from .eval import run_eval, run_redteam  # noqa: E402
from .llm import get_backend  # noqa: E402
from .schema import Transcript  # noqa: E402

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


async def _run_one(transcript_id: str | None = None) -> None:
    rows = [
        Transcript(**json.loads(line))
        for line in (DATA_DIR / "transcripts.jsonl").read_text().splitlines()
        if line.strip()
    ]
    if transcript_id:
        rows = [t for t in rows if t.transcript_id == transcript_id]
        if not rows:
            sys.exit(f"transcript_id {transcript_id!r} not found")
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
    if len(sys.argv) < 2:
        sys.exit("usage: cli.py {run [transcript_id] | eval | redteam}")
    cmd = sys.argv[1]
    if cmd == "run":
        tid = sys.argv[2] if len(sys.argv) > 2 else None
        asyncio.run(_run_one(tid))
    elif cmd == "eval":
        asyncio.run(run_eval())
    elif cmd == "redteam":
        asyncio.run(run_redteam())
    else:
        sys.exit(f"unknown command: {cmd!r}")


if __name__ == "__main__":
    main()
