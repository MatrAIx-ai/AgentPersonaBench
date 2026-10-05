import pytest

from playground.model_client import (
    DASHSCOPE_DEFAULT_BASE_URL,
    build_json_client,
    dashscope_openai_client_kwargs,
)
from playground.openai_client import OpenAIChatClient
from playground.user_sim.tool_client import OpenAIToolStepClient, build_tool_step_client


class _FakeOpenAI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.chat = object()


def test_dashscope_openai_client_kwargs_reads_env(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-dashscope-test")
    monkeypatch.delenv("DASHSCOPE_API_BASE", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)

    kwargs = dashscope_openai_client_kwargs("dashscope/qwen3.7-max")
    assert kwargs == {
        "model": "qwen3.7-max",
        "api_key": "sk-dashscope-test",
        "base_url": DASHSCOPE_DEFAULT_BASE_URL,
    }


def test_build_json_client_routes_dashscope_to_openai_compatible(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-dashscope-test")
    created: list[dict[str, str]] = []

    def fake_openai(**kwargs):
        created.append(kwargs)
        return _FakeOpenAI(**kwargs)

    monkeypatch.setattr("openai.OpenAI", fake_openai)

    client = build_json_client("dashscope/qwen3.6-plus-2026-04-02")
    assert isinstance(client, OpenAIChatClient)
    assert client.model == "qwen3.6-plus-2026-04-02"
    assert created == [
        {
            "api_key": "sk-dashscope-test",
            "base_url": DASHSCOPE_DEFAULT_BASE_URL,
            "max_retries": 8,
        }
    ]


def test_build_tool_step_client_routes_dashscope(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-dashscope-test")
    created: list[dict[str, str]] = []

    def fake_openai(**kwargs):
        created.append(kwargs)
        return _FakeOpenAI(**kwargs)

    monkeypatch.setattr("openai.OpenAI", fake_openai)

    client = build_tool_step_client("dashscope/deepseek-v4-pro")
    assert isinstance(client, OpenAIToolStepClient)
    assert client.model == "deepseek-v4-pro"
    assert created == [
        {
            "api_key": "sk-dashscope-test",
            "base_url": DASHSCOPE_DEFAULT_BASE_URL,
            "max_retries": 8,
        }
    ]


def test_build_json_client_requires_dashscope_key(monkeypatch):
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="DASHSCOPE_API_KEY"):
        build_json_client("dashscope/qwen-plus")
