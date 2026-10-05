import pytest
from types import SimpleNamespace

from playground.openai_client import (
    OpenAIChatClient,
    coerce_json,
    openai_model_uses_responses,
)


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeCompletion:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, content):
        self._c = content
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return _FakeCompletion(self._c)


class _FakeChat:
    def __init__(self, content):
        self.completions = _FakeCompletions(content)


class _FakeOpenAI:
    def __init__(self, content):
        self.chat = _FakeChat(content)


class _FakeResponses:
    def __init__(self, response):
        self.response = response
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return self.response


class _FakeResponsesOpenAI:
    def __init__(self, response):
        self.responses = _FakeResponses(response)
        self.chat = _FakeChat("unused")


def test_coerce_json_plain_and_fenced():
    assert coerce_json('{"a": 1}') == {"a": 1}
    assert coerce_json('```json\n{"a": 2}\n```') == {"a": 2}


def test_complete_json_parses_and_requests_json_mode():
    fake = _FakeOpenAI('{"message": "hi", "decision": "continue"}')
    client = OpenAIChatClient(model="gpt-4o-mini", client=fake)
    out = client.complete_json("sys", "user")
    assert out == {"message": "hi", "decision": "continue"}
    kw = fake.chat.completions.last_kwargs
    assert kw["model"] == "gpt-4o-mini"
    assert kw["response_format"] == {"type": "json_object"}
    assert kw["temperature"] == 0.7
    assert kw["messages"][0]["role"] == "system" and kw["messages"][1]["role"] == "user"


def test_complete_json_omits_temperature_for_gpt5():
    fake = _FakeOpenAI('{"ok": true}')
    client = OpenAIChatClient(model="gpt-5.5", client=fake, temperature=0.1)
    assert client.complete_json("sys", "user") == {"ok": True}
    kw = fake.chat.completions.last_kwargs
    assert "temperature" not in kw
    assert kw["model"] == "gpt-5.5"


def test_complete_json_uses_responses_for_gpt_5_6(monkeypatch):
    response = SimpleNamespace(
        status="completed", output_text='{"ok": true}', output=[]
    )
    fake = _FakeResponsesOpenAI(response)
    monkeypatch.setenv("LLM_REASONING_EFFORT", "high")

    client = OpenAIChatClient(
        model="gpt-5.6-sol", client=fake, temperature=0.1, timeout_seconds=45.5
    )

    assert client.complete_json("sys", "user") == {"ok": True}
    assert fake.responses.last_kwargs == {
        "model": "gpt-5.6-sol",
        "input": "user\n\nReturn only a valid JSON object.",
        "text": {"format": {"type": "json_object"}},
        "store": False,
        "timeout": 45.5,
        "instructions": "sys",
        "reasoning": {"effort": "high"},
    }
    assert fake.chat.completions.last_kwargs is None


def test_complete_json_raises_for_incomplete_responses_output(monkeypatch):
    response = SimpleNamespace(
        status="incomplete",
        incomplete_details=SimpleNamespace(reason="max_output_tokens"),
    )
    fake = _FakeResponsesOpenAI(response)
    monkeypatch.delenv("LLM_REASONING_EFFORT", raising=False)

    with pytest.raises(RuntimeError, match="max_output_tokens"):
        OpenAIChatClient(model="gpt-5.6", client=fake).complete_json("sys", "user")


def test_responses_model_detection_is_narrow():
    assert openai_model_uses_responses("gpt-5.6")
    assert openai_model_uses_responses("gpt-5.6-sol")
    assert openai_model_uses_responses("openai/gpt-5.6-terra")
    assert not openai_model_uses_responses("gpt-5.5")
    assert not openai_model_uses_responses("gpt-5.60")
    assert not openai_model_uses_responses("gpt-5.6foo")


def test_complete_json_omits_temperature_for_claude_opus_4_8():
    fake = _FakeOpenAI('{"ok": true}')
    client = OpenAIChatClient(
        model="anthropic/claude-opus-4-8", client=fake, temperature=0.1
    )
    assert client.complete_json("sys", "user") == {"ok": True}
    kw = fake.chat.completions.last_kwargs
    assert "temperature" not in kw
    assert kw["model"] == "anthropic/claude-opus-4-8"


def test_openai_model_is_reasoning_family_strips_vendor_prefix():
    from playground.openai_client import openai_model_is_reasoning_family

    assert openai_model_is_reasoning_family("gpt-5")
    assert openai_model_is_reasoning_family("gpt-5-mini")
    assert openai_model_is_reasoning_family("o1")
    assert openai_model_is_reasoning_family("o3")
    assert openai_model_is_reasoning_family("o4-mini")
    # A vendor prefix routes client selection, not model identity.
    assert openai_model_is_reasoning_family("openai/o4-mini")
    assert openai_model_is_reasoning_family("openai/gpt-5")
    assert not openai_model_is_reasoning_family("gpt-4o")
    assert not openai_model_is_reasoning_family("gpt-4.1")
    assert not openai_model_is_reasoning_family("claude-opus-4-8")


def test_openai_model_supports_custom_temperature_opus_rules():
    from playground.openai_client import openai_model_supports_custom_temperature

    assert openai_model_supports_custom_temperature("anthropic/claude-haiku-4-5")
    assert openai_model_supports_custom_temperature("anthropic/claude-sonnet-4-6")
    assert openai_model_supports_custom_temperature("claude-opus-4-1")
    assert not openai_model_supports_custom_temperature("anthropic/claude-opus-4-8")
    assert not openai_model_supports_custom_temperature("claude-opus-4-7")


def test_complete_json_raises_on_unparseable():
    client = OpenAIChatClient(model="gpt-4o-mini", client=_FakeOpenAI("not json at all"))
    with pytest.raises(ValueError):
        client.complete_json("s", "u")
