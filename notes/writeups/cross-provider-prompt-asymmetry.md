# A multi-provider eval caught a 27-point regression a single-provider eval would have shipped

Or: why the same prompt change can move Anthropic and OpenAI in opposite directions, and why that's not a curiosity — it's an engineering constraint.

## The setup

The [LLM alert triage](../../agents/llm-alert-triage/) project is an LLM agent that consumes synthetic SecOps alerts, calls into an MCP-served SIEM mock to enrich them, and emits a Pydantic-validated triage decision (severity, verdict, confidence, reasoning, recommended actions, MITRE techniques). It runs on either the Anthropic or the OpenAI API, selected by an environment variable. Same prompts, same dataset, same scoring — only the SDK and the model differ.

The eval harness scores each run on verdict accuracy, severity accuracy, MITRE technique IoU, schema validity, latency, and per-call cost. The first untuned run produced a baseline (Anthropic Sonnet 4.6: 67% verdict accuracy; OpenAI gpt-5-mini: 53%) and surfaced three concrete weaknesses both backends shared:

- **Severity over-calibration** — both predicted ≥1 step higher than ground truth on roughly 6 of 15 alerts.
- **MITRE technique over-generation** — both emitted 4–8 techniques per alert vs. ground truth's 1–2.
- **`needs_investigation` misses** — both labeled ambiguous activity (administrator running `Get-ADUser`, service installation at 02:14) as `true_positive` instead of flagging the ambiguity.

These are prompt issues, not model issues. Both backends had the same gaps, so the obvious next move was a single prompt-tuning iteration that addressed all three.

## The finding

The tuning iteration added an explicit severity-calibration table (info / low / medium / high / critical with concrete examples per level), a "common ambiguity cases" list naming the patterns that should resolve to `needs_investigation`, and a MITRE-pruning rule ("target 1-3 techniques; more than 3 is hedging").

Re-running both backends:

|                       | Anthropic Sonnet 4.6 | OpenAI gpt-5-mini |
|-----------------------|----------------------|-------------------|
| Verdict accuracy      | **−27pt** (67% → 40%)| 0 (53% → 53%)     |
| Severity accuracy     | +13pt (40% → 53%)    | **+20pt** (40% → 60%) |
| MITRE technique IoU   | −0.07 (0.19 → 0.12)  | **+0.17** (0.21 → 0.38) |
| Schema validity       | −20pt (100% → 80%)   | 0 (100% → 100%)   |
| Total cost / 15 alerts| +$0.26 ($0.26 → $0.52)| ≈0 ($0.06 → $0.058)|

Same prompt, opposite directions on the headline metric.

OpenAI gpt-5-mini broadly improved. ALERT-002 (mimikatz) emitted exactly `T1003.001` instead of four hedged techniques. ALERT-006 (SSH brute force) emitted `T1110.001` instead of nothing. ALERT-008 (remote WMI by service account) flipped from `true_positive` to the correct `needs_investigation`. No regressions.

Anthropic Sonnet 4.6 read the new "use `needs_investigation` when ambiguous" framing as permission to hedge, and started returning `needs_investigation` on cases that should be definitive: ALERT-005 (rundll32 loading from user temp — clear T1055 process injection), ALERT-014 (service account login during expected operating hours — should be `benign`). Verdict accuracy fell 27 points. Cost doubled because the model spent more thinking tokens on every alert.

## Why this matters

The regression is provider-specific, not noise. It reproduced run-over-run on the same dataset. The same tuning that made gpt-5-mini better made Sonnet 4.6 measurably worse, and on the metric that matters most operationally — does the agent classify the alert correctly.

This isn't a curiosity. It's an engineering constraint:

1. **A single shared prompt that's optimal for both providers may not exist.** Models have different default postures. Sonnet 4.6's default disposition is more decisive; nudging it toward "consider ambiguity" overshoots into hedging. gpt-5-mini's default is more cautious; the same nudge calibrates it correctly. The two models need different framings to land in the same operational range.

2. **Single-provider evals will quietly ship cross-provider regressions.** If the only eval was Anthropic-side, the tuning iteration would have looked like a small severity win. If the only eval was OpenAI-side, the same iteration would have looked like a clear improvement. Multi-provider evaluation is what made the asymmetry visible at all.

3. **The right next iteration isn't "find the one true prompt."** It's either provider-specific prompts (real engineering complexity, but cleanly correct) or a more carefully hedged shared prompt that identifies ambiguity cases without giving Sonnet permission to over-use `needs_investigation`. Both are real engineering decisions; the first one rolls back to the untuned baseline as the shipped state and treats the asymmetry as documented evidence.

## The takeaway

If your "AI for security" project runs on a single LLM provider, you don't actually know if your prompt is portable. That's fine for a demo; it's not fine for production where provider availability, cost, and policy can force a backend swap. The discipline that made this catchable was building the eval harness to score the same agent across two SDKs, on the same dataset, with the same scoring code, and committing the cross-provider results table as part of every PR's evidence.

The shipped state of the triage agent is the original untuned prompt — better Anthropic numbers, modest OpenAI numbers — with the tuned-prompt experiment recorded as evidence that tuning was tried, the asymmetry was the reason it was rolled back, and provider-specific prompts are the documented next iteration.

That last part is the senior-level finding. The eval surfaced exactly the regression it was built to catch. Without it, the tuning would have shipped, and any user who happened to be on Anthropic would have seen a quiet 27-point quality drop with no signal to attribute it to.

## Reproducing this

```bash
# In agents/llm-alert-triage/, with both keys configured:
LLM_BACKEND=anthropic make eval         # baseline, untuned prompt
LLM_BACKEND=openai    make eval         # baseline
# Edit the SYSTEM_PROMPT in src/alert_triage/agent.py to the elaborated
# calibration version (full text in the eval-results/eval-tuned-*.json archive
# and discussed in agents/llm-alert-triage/README.md).
LLM_BACKEND=anthropic make eval         # observe Anthropic regression
LLM_BACKEND=openai    make eval         # observe OpenAI improvement
```

Each run writes a JSON result file to `eval-results/`. The summary at the end of the run reports verdict accuracy, severity accuracy, MITRE IoU, schema validity, latency, and cost. Numbers above came from runs on 2026-05-07 (baseline) and 2026-05-07 (tuned).
