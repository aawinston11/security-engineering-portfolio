"""LLM backend abstraction.

Two backends are exposed via `LLM_BACKEND` env var:
- `anthropic` (default): the Anthropic API. Used for both `make run` and `make eval`.
- `ollama`: stub. Implemented after the LLM lab box is online; see
  notes/runbooks/llm-box-rebuild.md.

The agent loop in agent.py talks to a backend via the `messages_create` method,
which mirrors `anthropic.Anthropic().messages.create(**kwargs)`.
"""
from __future__ import annotations

import os
from typing import Any, Protocol

import anthropic


class LLMBackend(Protocol):
    name: str
    model: str

    def messages_create(self, **kwargs: Any) -> Any: ...


class AnthropicBackend:
    """Anthropic API. Sonnet 4.6 by default — the user's chosen default for cost.
    Override with `ANTHROPIC_MODEL` (e.g. `claude-opus-4-7` for max intelligence)."""

    name = "anthropic"

    def __init__(self, model: str | None = None) -> None:
        self.client = anthropic.Anthropic()
        self.model = model or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    def messages_create(self, **kwargs: Any) -> Any:
        kwargs.setdefault("model", self.model)
        return self.client.messages.create(**kwargs)


class OllamaBackend:
    """Stub — wires up after the LLM lab box has Ollama installed.

    Tracking work for implementation:
    - Translate Anthropic tool definitions to Ollama's OpenAI-compatible
      function-calling format.
    - Wrap the response so it looks like an Anthropic Message (stop_reason,
      content blocks with `tool_use` and `text` types).
    - Map output_config.format to Ollama's JSON mode + manual schema validation
      via the prompt; structured outputs from local models are model-dependent.
    See notes/runbooks/llm-box-rebuild.md, checkpoint 9-10 for context.
    """

    name = "ollama"

    def __init__(self, model: str | None = None, host: str | None = None) -> None:
        self.model = model or os.environ.get("OLLAMA_MODEL", "qwen2.5:14b-instruct-q4_K_M")
        self.host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")

    def messages_create(self, **kwargs: Any) -> Any:
        raise NotImplementedError(
            f"OllamaBackend not yet implemented (model={self.model!r}, host={self.host!r}). "
            "See notes/runbooks/llm-box-rebuild.md. Use LLM_BACKEND=anthropic for now."
        )


def get_backend() -> LLMBackend:
    backend = os.environ.get("LLM_BACKEND", "anthropic").lower()
    if backend == "anthropic":
        return AnthropicBackend()
    if backend == "ollama":
        return OllamaBackend()
    raise ValueError(f"Unknown LLM_BACKEND={backend!r} — expected 'anthropic' or 'ollama'.")
