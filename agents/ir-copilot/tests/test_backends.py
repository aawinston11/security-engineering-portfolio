"""LLM_BACKEND selection tests — no live API."""
from __future__ import annotations

import pytest

from ir_copilot.llm import (
    AnthropicBackend,
    OllamaBackend,
    OpenAIBackend,
    get_backend,
)


def test_default_is_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_BACKEND", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    llm = get_backend()
    assert isinstance(llm, AnthropicBackend)
    assert llm.model.startswith("claude-")


def test_openai_selected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BACKEND", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    llm = get_backend()
    assert isinstance(llm, OpenAIBackend)
    assert llm.model.startswith("gpt-")


def test_ollama_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BACKEND", "ollama")
    llm = get_backend()
    assert isinstance(llm, OllamaBackend)


def test_unknown_backend_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BACKEND", "claude-but-misspelled")
    with pytest.raises(ValueError, match="Unknown LLM_BACKEND"):
        get_backend()
