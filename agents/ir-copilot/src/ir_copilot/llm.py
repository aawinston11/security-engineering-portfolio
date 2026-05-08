"""LLM backend abstraction for the IR copilot.

Single-turn (no tool loops): the transcript is the entire input, the IR doc is
the entire output. Each backend exposes `generate()` which takes a system
prompt, the user content (formatted transcript), and the JSON schema for
structured output, and returns the raw text + usage telemetry.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Protocol

import anthropic


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    cache_creation_tokens: int = 0  # Anthropic only
    reasoning_tokens: int = 0  # OpenAI reasoning models only


@dataclass
class GenResult:
    text: str
    error: str | None = None
    usage: Usage = field(default_factory=Usage)


class LLMBackend(Protocol):
    name: str
    model: str

    async def generate(
        self,
        *,
        system: str,
        user_content: str,
        output_schema: dict[str, Any],
    ) -> GenResult: ...


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------

class AnthropicBackend:
    name = "anthropic"

    def __init__(self, model: str | None = None) -> None:
        self.client = anthropic.AsyncAnthropic()
        self.model = model or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    async def generate(
        self,
        *,
        system: str,
        user_content: str,
        output_schema: dict[str, Any],
    ) -> GenResult:
        usage = Usage()
        try:
            resp = await self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                system=system,
                messages=[{"role": "user", "content": user_content}],
                thinking={"type": "adaptive"},
                output_config={
                    "effort": "medium",
                    "format": {"type": "json_schema", "schema": output_schema},
                },
                cache_control={"type": "ephemeral"},
            )
        except Exception as e:  # noqa: BLE001
            return GenResult(text="", error=f"{type(e).__name__}: {e}", usage=usage)

        u = resp.usage
        usage.input_tokens = getattr(u, "input_tokens", 0) or 0
        usage.output_tokens = getattr(u, "output_tokens", 0) or 0
        usage.cached_tokens = getattr(u, "cache_read_input_tokens", 0) or 0
        usage.cache_creation_tokens = getattr(u, "cache_creation_input_tokens", 0) or 0

        text = "\n".join(b.text for b in resp.content if b.type == "text").strip()
        return GenResult(text=text, usage=usage)


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------

class OpenAIBackend:
    name = "openai"

    def __init__(self, model: str | None = None) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "openai package not installed. Run `make setup` (or `uv add openai`)."
            ) from e
        self.client = AsyncOpenAI()
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-5-mini")
        self.reasoning_effort = os.environ.get("OPENAI_REASONING_EFFORT", "medium").strip()

    async def generate(
        self,
        *,
        system: str,
        user_content: str,
        output_schema: dict[str, Any],
    ) -> GenResult:
        usage = Usage()
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "ir_doc",
                    "schema": output_schema,
                    "strict": True,
                },
            },
        }
        if self.reasoning_effort:
            kwargs["reasoning_effort"] = self.reasoning_effort

        try:
            resp = await self.client.chat.completions.create(**kwargs)
        except Exception as e:  # noqa: BLE001
            return GenResult(text="", error=f"{type(e).__name__}: {e}", usage=usage)

        u = resp.usage
        usage.input_tokens = getattr(u, "prompt_tokens", 0) or 0
        usage.output_tokens = getattr(u, "completion_tokens", 0) or 0
        ptd = getattr(u, "prompt_tokens_details", None)
        usage.cached_tokens = getattr(ptd, "cached_tokens", 0) or 0
        ctd = getattr(u, "completion_tokens_details", None)
        usage.reasoning_tokens = getattr(ctd, "reasoning_tokens", 0) or 0

        text = (resp.choices[0].message.content or "").strip()
        return GenResult(text=text, usage=usage)


# ---------------------------------------------------------------------------
# Ollama (stub)
# ---------------------------------------------------------------------------

class OllamaBackend:
    name = "ollama"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.environ.get("OLLAMA_MODEL", "qwen2.5:14b-instruct-q4_K_M")
        self.host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

    async def generate(self, **_: Any) -> GenResult:
        raise NotImplementedError(
            f"OllamaBackend not yet implemented (model={self.model!r}, host={self.host!r}). "
            "See notes/runbooks/llm-box-rebuild.md."
        )


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
