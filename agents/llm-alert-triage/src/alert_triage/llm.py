"""LLM backend abstraction for the triage agent.

Three backends, selected via `LLM_BACKEND` env var:
  - `anthropic` (default): Anthropic API. Default model `claude-sonnet-4-6`.
    Adaptive thinking + effort=medium, prompt caching on the system prompt.
  - `openai`: OpenAI Chat Completions API. Default model `gpt-5-mini`.
    `reasoning_effort=medium` (configurable) on reasoning-capable models.
  - `ollama`: stub. See notes/runbooks/llm-box-rebuild.md.

The Anthropic content-block model and OpenAI's flat tool_calls model don't
translate 1:1, so each backend owns its own agent loop. A backend exposes
`run_triage(...)` and the orchestrator in agent.py calls it.
"""
from __future__ import annotations

import json
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

import anthropic
from pydantic import ValidationError

from .schema import TriageDecision

# Triage decisions are small; 8K is plenty including adaptive thinking headroom.
MAX_TOKENS = 8192
# Safety cap: alert + a few tool round-trips + decision.
MAX_TURNS = 6


@dataclass
class GenericTool:
    """Backend-agnostic tool definition. Built from MCP `Tool` objects."""

    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class Usage:
    """Per-run token accounting. Some fields are provider-specific (and stay zero)."""

    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0  # Anthropic cache_read OR OpenAI cached prompt tokens
    cache_creation_tokens: int = 0  # Anthropic only
    reasoning_tokens: int = 0  # OpenAI reasoning models only


@dataclass
class TriageRunResult:
    """Result of one triage run on a single alert."""

    decision: TriageDecision | None
    schema_valid: bool
    tool_calls: int
    turns: int
    error: str | None
    raw_text: str | None
    usage: Usage = field(default_factory=Usage)


ExecuteTool = Callable[[str, dict[str, Any]], Awaitable[str]]


class LLMBackend(Protocol):
    name: str
    model: str

    async def run_triage(
        self,
        *,
        alert_payload: str,
        system_prompt: str,
        tools: list[GenericTool],
        output_schema: dict[str, Any],
        execute_tool: ExecuteTool,
    ) -> TriageRunResult: ...


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------

class AnthropicBackend:
    """Anthropic API. Sonnet 4.6 by default — the user-chosen cost-effective default.
    Override with `ANTHROPIC_MODEL` (e.g. `claude-opus-4-7` for max intelligence)."""

    name = "anthropic"

    def __init__(self, model: str | None = None) -> None:
        self.client = anthropic.AsyncAnthropic()
        self.model = model or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    async def run_triage(
        self,
        *,
        alert_payload: str,
        system_prompt: str,
        tools: list[GenericTool],
        output_schema: dict[str, Any],
        execute_tool: ExecuteTool,
    ) -> TriageRunResult:
        anthropic_tools = [
            {"name": t.name, "description": t.description, "input_schema": t.input_schema}
            for t in tools
        ]
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": alert_payload},
        ]
        usage = Usage()
        tool_calls = 0

        for turn in range(1, MAX_TURNS + 1):
            try:
                resp = await self.client.messages.create(
                    model=self.model,
                    max_tokens=MAX_TOKENS,
                    system=system_prompt,
                    messages=messages,
                    tools=anthropic_tools,
                    thinking={"type": "adaptive"},
                    output_config={
                        "effort": "medium",
                        "format": {"type": "json_schema", "schema": output_schema},
                    },
                    cache_control={"type": "ephemeral"},
                )
            except Exception as e:  # noqa: BLE001 — surface API errors in the result
                return TriageRunResult(
                    decision=None, schema_valid=False, tool_calls=tool_calls,
                    turns=turn, error=f"{type(e).__name__}: {e}",
                    raw_text=None, usage=usage,
                )

            u = resp.usage
            usage.input_tokens += getattr(u, "input_tokens", 0) or 0
            usage.output_tokens += getattr(u, "output_tokens", 0) or 0
            usage.cached_tokens += getattr(u, "cache_read_input_tokens", 0) or 0
            usage.cache_creation_tokens += getattr(u, "cache_creation_input_tokens", 0) or 0

            if resp.stop_reason == "tool_use":
                tool_use_blocks = [b for b in resp.content if b.type == "tool_use"]
                # Anthropic 400s on `messages: text content blocks must be non-empty`
                # if we echo back an assistant turn that includes an empty text block.
                # Adaptive-thinking responses sometimes contain a zero-length text block
                # alongside thinking/tool_use blocks — drop those before re-sending.
                clean_assistant_content = [
                    b for b in resp.content
                    if not (b.type == "text" and not (getattr(b, "text", "") or "").strip())
                ]
                messages.append({"role": "assistant", "content": clean_assistant_content})

                tool_results = []
                for tu in tool_use_blocks:
                    tool_calls += 1
                    try:
                        output = await execute_tool(tu.name, dict(tu.input))
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tu.id,
                            "content": output,
                        })
                    except Exception as e:  # noqa: BLE001
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tu.id,
                            "content": f"tool error: {type(e).__name__}: {e}",
                            "is_error": True,
                        })
                messages.append({"role": "user", "content": tool_results})
                continue

            # Terminal stop_reason: parse the final text as TriageDecision.
            text = "\n".join(b.text for b in resp.content if b.type == "text").strip()
            if not text:
                return TriageRunResult(
                    decision=None, schema_valid=False, tool_calls=tool_calls,
                    turns=turn, error=f"no text in final response (stop_reason={resp.stop_reason!r})",
                    raw_text=None, usage=usage,
                )
            try:
                decision = TriageDecision.model_validate_json(text)
                return TriageRunResult(
                    decision=decision, schema_valid=True, tool_calls=tool_calls,
                    turns=turn, error=None, raw_text=text, usage=usage,
                )
            except ValidationError as ve:
                return TriageRunResult(
                    decision=None, schema_valid=False, tool_calls=tool_calls,
                    turns=turn, error=f"schema validation failed: {ve}",
                    raw_text=text, usage=usage,
                )

        return TriageRunResult(
            decision=None, schema_valid=False, tool_calls=tool_calls,
            turns=MAX_TURNS, error=f"max turns ({MAX_TURNS}) exceeded",
            raw_text=None, usage=usage,
        )


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------

class OpenAIBackend:
    """OpenAI Chat Completions API. Default model `gpt-5-mini`.

    `OPENAI_REASONING_EFFORT` (default `medium`) is passed as `reasoning_effort`
    on reasoning-capable models. Set to empty string to omit (e.g. for non-reasoning
    models that 400 on the parameter).
    """

    name = "openai"

    def __init__(self, model: str | None = None) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError as e:  # pragma: no cover — install issue
            raise ImportError(
                "openai package not installed. Run `make setup` (or `uv add openai`)."
            ) from e
        self.client = AsyncOpenAI()
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-5-mini")
        self.reasoning_effort = os.environ.get("OPENAI_REASONING_EFFORT", "medium").strip()

    async def run_triage(
        self,
        *,
        alert_payload: str,
        system_prompt: str,
        tools: list[GenericTool],
        output_schema: dict[str, Any],
        execute_tool: ExecuteTool,
    ) -> TriageRunResult:
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                },
            }
            for t in tools
        ]
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": alert_payload},
        ]
        usage = Usage()
        tool_calls = 0

        kwargs_extra: dict[str, Any] = {}
        if self.reasoning_effort:
            kwargs_extra["reasoning_effort"] = self.reasoning_effort

        for turn in range(1, MAX_TURNS + 1):
            try:
                resp = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=openai_tools,
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "triage_decision",
                            "schema": output_schema,
                            "strict": True,
                        },
                    },
                    **kwargs_extra,
                )
            except Exception as e:  # noqa: BLE001
                return TriageRunResult(
                    decision=None, schema_valid=False, tool_calls=tool_calls,
                    turns=turn, error=f"{type(e).__name__}: {e}",
                    raw_text=None, usage=usage,
                )

            u = resp.usage
            usage.input_tokens += getattr(u, "prompt_tokens", 0) or 0
            usage.output_tokens += getattr(u, "completion_tokens", 0) or 0
            ptd = getattr(u, "prompt_tokens_details", None)
            usage.cached_tokens += getattr(ptd, "cached_tokens", 0) or 0
            ctd = getattr(u, "completion_tokens_details", None)
            usage.reasoning_tokens += getattr(ctd, "reasoning_tokens", 0) or 0

            msg = resp.choices[0].message

            if not msg.tool_calls:
                content = msg.content or ""
                if not content:
                    return TriageRunResult(
                        decision=None, schema_valid=False, tool_calls=tool_calls,
                        turns=turn, error=f"empty content (finish_reason={resp.choices[0].finish_reason!r})",
                        raw_text=None, usage=usage,
                    )
                try:
                    decision = TriageDecision.model_validate_json(content)
                    return TriageRunResult(
                        decision=decision, schema_valid=True, tool_calls=tool_calls,
                        turns=turn, error=None, raw_text=content, usage=usage,
                    )
                except ValidationError as ve:
                    return TriageRunResult(
                        decision=None, schema_valid=False, tool_calls=tool_calls,
                        turns=turn, error=f"schema validation failed: {ve}",
                        raw_text=content, usage=usage,
                    )

            # Append the assistant turn (must echo tool_calls back).
            messages.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            })

            for tc in msg.tool_calls:
                tool_calls += 1
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError as e:
                    output = f"tool error: malformed arguments JSON: {e}"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": output,
                    })
                    continue
                try:
                    output = await execute_tool(tc.function.name, args)
                except Exception as e:  # noqa: BLE001
                    output = f"tool error: {type(e).__name__}: {e}"
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": output,
                })

        return TriageRunResult(
            decision=None, schema_valid=False, tool_calls=tool_calls,
            turns=MAX_TURNS, error=f"max turns ({MAX_TURNS}) exceeded",
            raw_text=None, usage=usage,
        )


# ---------------------------------------------------------------------------
# Ollama (stub)
# ---------------------------------------------------------------------------

class OllamaBackend:
    """Stub — wires up after the LLM lab box has Ollama installed.
    See notes/runbooks/llm-box-rebuild.md. Use LLM_BACKEND=anthropic or openai for now."""

    name = "ollama"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.environ.get("OLLAMA_MODEL", "qwen2.5:14b-instruct-q4_K_M")
        self.host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

    async def run_triage(self, **_: Any) -> TriageRunResult:
        raise NotImplementedError(
            f"OllamaBackend not yet implemented (model={self.model!r}, host={self.host!r}). "
            "See notes/runbooks/llm-box-rebuild.md."
        )


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------

def get_backend() -> LLMBackend:
    backend = os.environ.get("LLM_BACKEND", "anthropic").lower()
    if backend == "anthropic":
        return AnthropicBackend()
    if backend == "openai":
        return OpenAIBackend()
    if backend == "ollama":
        return OllamaBackend()
    raise ValueError(
        f"Unknown LLM_BACKEND={backend!r} — expected 'anthropic', 'openai', or 'ollama'."
    )
