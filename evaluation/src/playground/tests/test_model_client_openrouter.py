import pytest

from playground import model_client
from playground.openai_client import OpenAIChatClient
from playground.user_sim.tool_client import OpenAIToolStepClient, build_tool_step_client


class _FakeOpenAI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.chat = object()


def test_openrouter_model_id_preserves_provider_model_path():
    assert (
        model_client.openrouter_model_id("openrouter/z-ai/glm-4.7")
        == "z-ai/glm-4.7"
    )


def test_openrouter_model_id_preserves_anthropic_model_path():
    assert (
        model_client.openrouter_model_id(
            "openrouter/anthropic/claude-haiku-4.5"
        )
        == "anthropic/claude-haiku-4.5"
    )


def test_openrouter_openai_client_kwargs_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        model_client.openrouter_openai_client_kwargs(
            "openrouter/z-ai/glm-4.7"
        )


def test_openrouter_api_base_overrides_default(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-openrouter-test")
    monkeypatch.setenv("OPENROUTER_API_BASE", "https://openrouter.test/v1")

    kwargs = model_client.openrouter_openai_client_kwargs(
        "openrouter/z-ai/glm-4.7"
    )
    assert kwargs == {
        "model": "z-ai/glm-4.7",
        "api_key": "sk-openrouter-test",
        "base_url": "https://openrouter.test/v1",
    }


def test_build_json_client_routes_openrouter_to_openai_compatible(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-openrouter-test")
    monkeypatch.delenv("OPENROUTER_API_BASE", raising=False)
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    created: list[dict[str, str]] = []

    def fake_openai(**kwargs):
        created.append(kwargs)
        return _FakeOpenAI(**kwargs)

    monkeypatch.setattr("openai.OpenAI", fake_openai)

    client = model_client.build_json_client("openrouter/z-ai/glm-4.7")
    assert isinstance(client, OpenAIChatClient)
    assert client.model == "z-ai/glm-4.7"
    assert created == [
        {
            "api_key": "sk-openrouter-test",
            "base_url": model_client.OPENROUTER_DEFAULT_BASE_URL,
            "max_retries": 8,
        }
    ]


def test_build_tool_step_client_routes_openrouter_to_openai_compatible(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-openrouter-test")
    monkeypatch.delenv("OPENROUTER_API_BASE", raising=False)
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    created: list[dict[str, str]] = []

    def fake_openai(**kwargs):
        created.append(kwargs)
        return _FakeOpenAI(**kwargs)

    monkeypatch.setattr("openai.OpenAI", fake_openai)

    client = build_tool_step_client("openrouter/z-ai/glm-4.7")
    assert isinstance(client, OpenAIToolStepClient)
    assert client.model == "z-ai/glm-4.7"
    assert created == [
        {
            "api_key": "sk-openrouter-test",
            "base_url": model_client.OPENROUTER_DEFAULT_BASE_URL,
            "max_retries": 8,
        }
    ]


def test_openrouter_base_url_alias_configures_json_client(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-openrouter-test")
    monkeypatch.delenv("OPENROUTER_API_BASE", raising=False)
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://alias.openrouter.test/v1")
    created: list[dict[str, str]] = []

    def fake_openai(**kwargs):
        created.append(kwargs)
        return _FakeOpenAI(**kwargs)

    monkeypatch.setattr("openai.OpenAI", fake_openai)

    client = model_client.build_json_client("openrouter/z-ai/glm-4.7")
    assert isinstance(client, OpenAIChatClient)
    assert created == [
        {
            "api_key": "sk-openrouter-test",
            "base_url": "https://alias.openrouter.test/v1",
            "max_retries": 8,
        }
    ]


def test_openrouter_api_base_wins_over_alias_for_tool_client(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-openrouter-test")
    monkeypatch.setenv("OPENROUTER_API_BASE", "https://primary.openrouter.test/v1")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://alias.openrouter.test/v1")
    created: list[dict[str, str]] = []

    def fake_openai(**kwargs):
        created.append(kwargs)
        return _FakeOpenAI(**kwargs)

    monkeypatch.setattr("openai.OpenAI", fake_openai)

    client = build_tool_step_client("openrouter/z-ai/glm-4.7")
    assert isinstance(client, OpenAIToolStepClient)
    assert created == [
        {
            "api_key": "sk-openrouter-test",
            "base_url": "https://primary.openrouter.test/v1",
            "max_retries": 8,
        }
    ]


def test_openai_base_url_does_not_change_openrouter_routing(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-openrouter-test")
    monkeypatch.delenv("OPENROUTER_API_BASE", raising=False)
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)
    monkeypatch.setenv("OPENAI_BASE_URL", "https://openai-proxy.test/v1")
    created: list[dict[str, str]] = []

    def fake_openai(**kwargs):
        created.append(kwargs)
        return _FakeOpenAI(**kwargs)

    monkeypatch.setattr("openai.OpenAI", fake_openai)

    client = model_client.build_json_client("openrouter/z-ai/glm-4.7")
    assert isinstance(client, OpenAIChatClient)
    assert client.model == "z-ai/glm-4.7"
    assert created == [
        {
            "api_key": "sk-openrouter-test",
            "base_url": model_client.OPENROUTER_DEFAULT_BASE_URL,
            "max_retries": 8,
        }
    ]


def test_openrouter_gpt_5_6_does_not_assume_responses_support(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-openrouter-test")
    monkeypatch.delenv("OPENROUTER_API_BASE", raising=False)
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)
    monkeypatch.setattr("openai.OpenAI", lambda **kwargs: _FakeOpenAI(**kwargs))

    json_client = model_client.build_json_client("openrouter/openai/gpt-5.6-sol")
    tool_client = build_tool_step_client("openrouter/openai/gpt-5.6-sol")

    assert json_client.use_responses_api is False
    assert tool_client.use_responses_api is False
