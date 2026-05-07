"""Backend selection tests — no live API."""
from __future__ import annotations

import pytest

from alert_triage.llm import (
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
    assert llm.name == "anthropic"
    assert llm.model.startswith("claude-")


def test_openai_selected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BACKEND", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    llm = get_backend()
    assert isinstance(llm, OpenAIBackend)
    assert llm.name == "openai"
    assert llm.model.startswith("gpt-")


def test_openai_model_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BACKEND", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5")
    llm = get_backend()
    assert llm.model == "gpt-5"


def test_anthropic_model_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BACKEND", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-opus-4-7")
    llm = get_backend()
    assert llm.model == "claude-opus-4-7"


def test_ollama_selected_but_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BACKEND", "ollama")
    llm = get_backend()
    assert isinstance(llm, OllamaBackend)
    assert llm.name == "ollama"


def test_unknown_backend_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BACKEND", "claude-haiku-but-misspelled")
    with pytest.raises(ValueError, match="Unknown LLM_BACKEND"):
        get_backend()
