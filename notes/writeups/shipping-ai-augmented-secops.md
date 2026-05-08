# Shipping AI-augmented SecOps: notes from a four-project portfolio

The state of "AI for security" right now is mostly demos. Promising demos. But demos. The gap between "the model writes a verdict on a screenshot" and "the model is trustworthy enough to leave running" is the gap this portfolio tried to close. Four projects, four different shapes of agentic SecOps work, all evaluated against synthetic data with the same disciplines applied: pinned schemas, labeled datasets, cross-provider eval, evidence-first README claims.

What follows is what those projects actually taught me — three findings that matter beyond the individual code, plus what I'd do next.

## The four projects

[**MCP Security Tooling Server**](../../agents/mcp-security-tooling/) — a Model Context Protocol server exposing a synthetic SIEM/EDR API to LLM agents over stdio. Five read tools (search events, search alerts, fetch alert by ID, list hosts, enrich indicator) backed by four committed datasets, auth-scoped, with an HMAC-chained tamper-evident audit log. The audit log is the part most "AI for security" demos skip and the part security teams will care about first.

[**LLM Alert Triage**](../../agents/llm-alert-triage/) — a triage agent that consumes synthetic SecOps alerts, calls into the MCP server for enrichment, and emits Pydantic-validated decisions mapped to MITRE ATT&CK. Anthropic + OpenAI backends. Eval harness on a 15-alert labeled dataset scoring verdict accuracy, severity, MITRE technique IoU, latency, and cost across both providers.

[**IR Copilot**](../../agents/ir-copilot/) — a single-turn copilot that ingests Slack-style incident-channel transcripts and emits structured IR docs. Built around a three-layer prompt-injection defense (data-not-instructions framing + schema-constrained output + injection acknowledgement). Red-team eval set with three injection categories that both backends defeated 6/6.

[**Detection-as-Code**](../../detection/detection-as-code/) — a Sigma corpus across five ATT&CK tactics with positive and negative log fixtures per rule, an in-process Sigma evaluator, and a purple-team runner that asserts every rule fires on its positives and stays silent on its negatives. CI fails on rule regressions, not just code regressions.

## Finding 1: eval discipline beats demo screenshots

The single highest-leverage decision in the portfolio was building a real eval harness for the triage agent before tuning a single prompt. Nothing about a triage demo with a hand-picked alert tells you how the agent behaves on the *next* alert. A 15-alert labeled dataset with deterministic synthetic backing data tells you instantly:

- Verdict accuracy: 67% on Anthropic Sonnet 4.6 baseline, 53% on OpenAI gpt-5-mini.
- Severity over-calibration: both providers ~40% exact match, both biased high.
- Schema validity: 100% on both — the strict json-schema constraint at the API layer plus Pydantic on the client side really does eliminate malformed output.

Those numbers aren't great. That's the point — they're an *honest baseline*, and now I can iterate against them. Without the harness, I'd have shipped a demo that shows three impressive triages and hides the seven where the model hedged or hallucinated MITRE techniques.

The same discipline applied to the IR copilot. Six red-team transcripts (status-flip injection, prompt-leak injection, destructive-action injection) with negative-assertion expectations: status not in {false_alarm, resolved}, severity not downgraded, no forbidden text in any IR doc field. Both backends passed all six. That's a falsifiable claim — anyone can re-run `make redteam` and check.

The takeaway: if your "AI for security" project has no labeled dataset and no harness that runs it in CI, you don't actually know what you've built. You have a demo.

## Finding 2: multi-provider eval is engineering discipline, not a curiosity

I almost shipped a 27-point Anthropic verdict-accuracy regression because of a single prompt-tuning iteration that looked good on OpenAI.

The full story is in [cross-provider-prompt-asymmetry.md](cross-provider-prompt-asymmetry.md). The short version: the same prompt change that improved gpt-5-mini's severity calibration by 20 points and MITRE technique IoU by 0.17 caused Sonnet 4.6 to over-use `needs_investigation`, dropping verdict accuracy from 67% to 40%. Same prompt, opposite directions.

If the only eval was Anthropic, the iteration would have looked like a quality regression and I'd have rolled it back. If the only eval was OpenAI, the iteration would have looked like a clean win and I'd have shipped it. The multi-provider eval — same agent code, same dataset, same scoring, both SDKs — is what made the asymmetry visible at all.

The eventual fix: provider-specific prompts via `PROMPTS_BY_BACKEND` in the agent. Anthropic gets the spare baseline. OpenAI gets the calibrated version. Each backend lands at its individual best. The asymmetry isn't a bug; it's a fact about how different model families have different default postures, and the right engineering response is a small per-provider adapter.

The broader takeaway: if your portfolio runs on a single LLM provider, you don't actually know if your prompt is portable. That's fine for a demo, not fine for production where availability, cost, and policy can force a backend swap.

## Finding 3: prompt injection is a real defensive surface

The IR copilot was the project I was most uncertain about going in. The structured-output story (Pydantic + JSON schema) is well-trodden. The interesting question was whether you can actually make a copilot ignore instructions found in the data it's analyzing.

Three layers turned out to be enough on the test set:

1. **Frame the input as data**, not instructions. Wrap the transcript in `<TRANSCRIPT>...</TRANSCRIPT>` delimiters and JSON-encode the user/text fields so an injected angle bracket can't break the envelope.
2. **Schema-constrain the output**. There are no free-form fields where an injected action could be smuggled out. The `status` field is an enum. The `action_items` is a typed array. The model can't trojan an "approve all containment" into the response without lying about the schema.
3. **Ask the model to acknowledge injections** in the `summary` field. This gives the eval an observable positive signal in addition to the negative checks, and turned out to work on both providers across all three injection categories.

6/6 red-team cases passed across Anthropic and OpenAI. None of the IR doc fields contained forbidden text on any run. Each model's `summary` explicitly noted it had ignored injection-shaped content.

The takeaway: prompt injection isn't an exotic threat for an IR copilot — the transcript IS the threat surface. The defense is small enough to fit in a system prompt + a strict response schema, and the red-team set makes the defense measurable.

## What's next

Three threads I'd pick up next:

**The Ollama backend.** Both agents have a stubbed Ollama path, gated behind a local LLM lab box rebuild. The interesting comparison isn't "two API providers" — it's "two API providers plus one self-hosted model." Once that lands, the eval table becomes a real cost-vs-quality decision for any team considering local inference for cost or compliance reasons.

**Real Atomic Red Team execution for the detection corpus.** The current purple-team runner uses synthetic fixtures shaped like ART output. The runner shape doesn't change when you swap fixtures for real ART executions against a controlled lab; what changes is the realism of the positives. That's the obvious next iteration when a target VM is available.

**Tooling beyond read.** The MCP server's five tools are all read-only. Containment-class tools (`quarantine_host`, `disable_account`, `block_indicator`) require an `act:` scope and a different audit treatment. They're explicit no-ops in the synthetic SIEM today, but adding them and wiring the act-scope check end-to-end would close another loop — the agent would not just diagnose, it would propose specific actions through a clearly-scoped surface.

## Summary

Four projects, three pillars:
- AI / agentic security: MCP server + alert triage + IR copilot
- Detection & automation: detection-as-code with purple-team validation
- Foundations: hardening role

What ties them together isn't the LLM — half the portfolio doesn't even use one. What ties them together is the discipline: labeled datasets, pinned schemas, evidence-first claims in every README, eval harnesses that fail in CI, and an honest accounting of trade-offs (prompt-tuning iteration data, asymmetric provider behavior, the limits of a synthetic backing corpus).

The takeaway I want a recruiter or a hiring manager to leave with: this isn't "I tried Claude on some alerts." This is "I built four shippable shapes of agentic SecOps tooling, evaluated each against ground truth across two providers, and the README claims are falsifiable in 60 seconds."

Run any of them with `make eval` and check.
