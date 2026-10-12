"""Tests for persona model resolution."""

from __future__ import annotations

from playground.persona_model import resolve_persona_model
from playground.types import DEFAULT_PERSONA_MODEL


def test_resolve_persona_model_prefers_harbor_model_name(monkeypatch) -> None:
    monkeypatch.setenv("MATRIX_PERSONA_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("MATRIX_CHATBOT_PERSONA_MODEL", "anthropic/claude-haiku-4-5")

    assert (
        resolve_persona_model(model_name="anthropic/claude-sonnet-4-6")
        == "anthropic/claude-sonnet-4-6"
    )


def test_resolve_persona_model_uses_chat_env_when_enabled(monkeypatch) -> None:
    monkeypatch.delenv("MATRIX_PERSONA_MODEL", raising=False)
    monkeypatch.delenv("MATRIX_HARBOR_PERSONA_MODEL", raising=False)
    monkeypatch.setenv("MATRIX_CHATBOT_PERSONA_MODEL", "openai/gpt-4o")

    assert resolve_persona_model(include_chat_env=True) == "openai/gpt-4o"


def test_resolve_persona_model_ignores_chat_env_for_survey(monkeypatch) -> None:
    monkeypatch.delenv("MATRIX_PERSONA_MODEL", raising=False)
    monkeypatch.delenv("MATRIX_HARBOR_PERSONA_MODEL", raising=False)
    monkeypatch.setenv("MATRIX_CHATBOT_PERSONA_MODEL", "openai/gpt-4o")

    assert resolve_persona_model(include_chat_env=False) == DEFAULT_PERSONA_MODEL


def test_resolve_persona_model_uses_persona_env(monkeypatch) -> None:
    monkeypatch.setenv("MATRIX_PERSONA_MODEL", "openai/gpt-4o-mini")

    assert resolve_persona_model() == "openai/gpt-4o-mini"
