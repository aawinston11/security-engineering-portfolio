"""Eval harness: run the agent against the labeled dataset and score the results.

Metrics:
- verdict accuracy (predicted == ground truth)
- severity accuracy (exact match)
- MITRE technique IoU (intersection over union of T-codes)
- schema validation rate (Pydantic parsed cleanly)
- false-positive rate: predicted true_positive when truth is benign / false_positive
- per-alert latency, total cost (Anthropic backend only)

Cost is computed from `usage` per-call. Sonnet 4.6 baseline: $3/M input, $15/M
output, ~$0.30/M for cache reads, ~$3.75/M for cache writes (1.25x input).
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .agent import TriageResult, triage_alert
from .llm import LLMBackend, get_backend
from .mcp_client import mcp_session
from .schema import Alert, GroundTruth

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
RESULTS_DIR = Path(__file__).resolve().parents[2] / "eval-results"

# Per-million-token rates for Anthropic models we actually use here.
# Cache-read ~ 0.1x input; cache-write ~ 1.25x input (5-min TTL).
ANTHROPIC_PRICE_PER_M = {
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-7": {"input": 5.00, "output": 25.00},
    "claude-opus-4-6": {"input": 5.00, "output": 25.00},
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
}


@dataclass
class ScoredResult:
    alert_id: str
    predicted_verdict: str | None
    predicted_severity: str | None
    predicted_techniques: list[str] = field(default_factory=list)
    expected_verdict: str = ""
    expected_severity: str = ""
    expected_techniques: list[str] = field(default_factory=list)
    verdict_match: bool = False
    severity_match: bool = False
    technique_iou: float = 0.0
    schema_valid: bool = False
    latency_seconds: float = 0.0
    tool_calls: int = 0
    cost_usd: float = 0.0
    error: str | None = None


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _iou(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    union = sa | sb
    if not union:
        return 0.0
    return len(sa & sb) / len(union)


def _cost_usd(result: TriageResult, model: str) -> float:
    rates = ANTHROPIC_PRICE_PER_M.get(model)
    if not rates:
        return 0.0
    in_rate = rates["input"]
    out_rate = rates["output"]
    # Standard input + output, plus cache-tier adjustments.
    cost = (
        result.input_tokens * in_rate
        + result.output_tokens * out_rate
        + result.cache_read_input_tokens * (in_rate * 0.10)
        + result.cache_creation_input_tokens * (in_rate * 1.25)
    ) / 1_000_000
    return round(cost, 6)


def _score_one(
    alert: Alert,
    truth: GroundTruth,
    result: TriageResult,
    model: str,
) -> ScoredResult:
    decision = result.decision
    return ScoredResult(
        alert_id=alert.alert_id,
        predicted_verdict=decision.verdict if decision else None,
        predicted_severity=decision.severity if decision else None,
        predicted_techniques=decision.mitre_techniques if decision else [],
        expected_verdict=truth.verdict,
        expected_severity=truth.severity,
        expected_techniques=truth.mitre_techniques,
        verdict_match=bool(decision and decision.verdict == truth.verdict),
        severity_match=bool(decision and decision.severity == truth.severity),
        technique_iou=_iou(decision.mitre_techniques, truth.mitre_techniques) if decision else 0.0,
        schema_valid=result.schema_valid,
        latency_seconds=round(result.latency_seconds, 2),
        tool_calls=result.tool_calls,
        cost_usd=_cost_usd(result, model),
        error=result.error,
    )


async def run_eval() -> dict:
    alerts = [Alert(**row) for row in _load_jsonl(DATA_DIR / "alerts.jsonl")]
    truths_by_id = {
        row["alert_id"]: GroundTruth(**row)
        for row in _load_jsonl(DATA_DIR / "ground_truth.jsonl")
    }

    llm = get_backend()
    print(f"Backend: {llm.name} / {llm.model}")
    print(f"Dataset: {DATA_DIR / 'alerts.jsonl'} ({len(alerts)} alerts)\n")

    started = time.monotonic()
    scored: list[ScoredResult] = []

    async with mcp_session() as session:
        for i, alert in enumerate(alerts, 1):
            truth = truths_by_id.get(alert.alert_id)
            if truth is None:
                print(f"[{i}/{len(alerts)}] {alert.alert_id} — no ground truth, skipping")
                continue

            print(f"[{i}/{len(alerts)}] {alert.alert_id} ({alert.name})")
            result = await triage_alert(alert, llm=llm, session=session)
            row = _score_one(alert, truth, result, llm.model)
            scored.append(row)

            verdict_str = row.predicted_verdict or "ERROR"
            sev_str = row.predicted_severity or "?"
            techs = ",".join(row.predicted_techniques) or "(none)"
            print(
                f"  predicted: {verdict_str} / {sev_str} / {techs} "
                f"({row.tool_calls} tool calls, {row.latency_seconds}s, ${row.cost_usd:.4f})"
            )
            print(
                f"  expected:  {row.expected_verdict} / {row.expected_severity} / "
                f"{','.join(row.expected_techniques) or '(none)'}"
            )
            marks = (
                f"{'OK' if row.verdict_match else 'X'} verdict  "
                f"{'OK' if row.severity_match else 'X'} severity  "
                f"IoU={row.technique_iou:.2f}  "
                f"{'schema-OK' if row.schema_valid else 'schema-FAIL'}"
            )
            if row.error:
                marks += f"  err: {row.error[:80]}"
            print(f"  {marks}\n")

    summary = _summarize(scored)
    summary["backend"] = llm.name
    summary["model"] = llm.model
    summary["wall_clock_seconds"] = round(time.monotonic() - started, 2)

    _print_summary(summary)
    _save_results(scored, summary)
    return summary


def _summarize(rows: list[ScoredResult]) -> dict:
    n = len(rows)
    if n == 0:
        return {"total": 0}
    verdict_acc = sum(1 for r in rows if r.verdict_match) / n
    sev_acc = sum(1 for r in rows if r.severity_match) / n
    schema_acc = sum(1 for r in rows if r.schema_valid) / n
    avg_iou = sum(r.technique_iou for r in rows) / n
    avg_latency = sum(r.latency_seconds for r in rows) / n
    total_cost = sum(r.cost_usd for r in rows)
    fp = sum(
        1
        for r in rows
        if r.predicted_verdict == "true_positive"
        and r.expected_verdict in ("benign", "false_positive")
    )
    return {
        "total": n,
        "verdict_accuracy": round(verdict_acc, 3),
        "severity_accuracy": round(sev_acc, 3),
        "mitre_iou_avg": round(avg_iou, 3),
        "schema_validity": round(schema_acc, 3),
        "false_positives_called": fp,
        "avg_latency_seconds": round(avg_latency, 2),
        "total_cost_usd": round(total_cost, 4),
    }


def _print_summary(summary: dict) -> None:
    print("=== Summary ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")


def _save_results(rows: list[ScoredResult], summary: dict) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    payload = {"summary": summary, "rows": [asdict(r) for r in rows]}
    out = RESULTS_DIR / f"eval-{stamp}.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {out.relative_to(Path.cwd()) if out.is_relative_to(Path.cwd()) else out}")
