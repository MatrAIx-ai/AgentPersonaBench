from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

import llm_client


class _FakeResponses:
    def __init__(self, response):
        self.response = response
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return self.response


class _FakeCompletions:
    def __init__(self, content="legacy reply"):
        self.content = content
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))],
            usage=SimpleNamespace(
                prompt_tokens=3, completion_tokens=2, total_tokens=5
            ),
        )


class _FakeOpenAI:
    def __init__(self, response):
        self.responses = _FakeResponses(response)
        self.chat = SimpleNamespace(completions=_FakeCompletions())


def _completed_response(*, output_text="response reply", output=None):
    return SimpleNamespace(
        status="completed",
        output_text=output_text,
        output=[] if output is None else output,
        usage=SimpleNamespace(input_tokens=7, output_tokens=4, total_tokens=11),
    )


def test_gpt_5_6_text_uses_responses_and_records_usage(monkeypatch):
    import openai

    fake = _FakeOpenAI(_completed_response())
    created = []

    def make_client(**kwargs):
        created.append(kwargs)
        return fake

    monkeypatch.setattr(openai, "OpenAI", make_client)
    monkeypatch.setenv("LLM_REASONING_EFFORT", "medium")
    llm_client.reset_call_log()

    result = llm_client._chat_openai(
        [
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "hello"},
        ],
        "gpt-5.6-sol",
        4321,
        0.6,
        "test-token",
        45,
    )

    assert result == "response reply"
    assert created == [{"api_key": "test-token", "timeout": 45}]
    assert fake.responses.last_kwargs == {
        "model": "gpt-5.6-sol",
        "input": [{"role": "user", "content": "hello"}],
        "max_output_tokens": 4321,
        "store": False,
        "instructions": "system prompt",
        "reasoning": {"effort": "medium"},
    }
    assert fake.chat.completions.last_kwargs is None
    assert llm_client.call_log_summary() == {
        "calls": 1,
        "total_tokens": 11,
        "prompt_tokens": 7,
        "completion_tokens": 4,
        "latency_s": llm_client.call_log_summary()["latency_s"],
    }


def test_gpt_5_6_text_reads_nested_output_fallback(monkeypatch):
    import openai

    response = _completed_response(
        output_text="",
        output=[
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": "nested "},
                    {"type": "output_text", "text": "reply"},
                ],
            }
        ],
    )
    fake = _FakeOpenAI(response)
    monkeypatch.setattr(openai, "OpenAI", lambda **_kwargs: fake)
    monkeypatch.delenv("LLM_REASONING_EFFORT", raising=False)

    result = llm_client._chat_openai(
        [{"role": "user", "content": "hello"}],
        "gpt-5.6",
        100,
        0.2,
        "test-token",
        45,
    )

    assert result == "nested reply"
    assert "reasoning" not in fake.responses.last_kwargs


@pytest.mark.parametrize("output_text", ["partial", ""])
def test_gpt_5_6_max_output_tokens_returns_available_text(
    monkeypatch, caplog, output_text
):
    import openai

    response = SimpleNamespace(
        status="incomplete",
        incomplete_details=SimpleNamespace(reason="max_output_tokens"),
        output_text=output_text,
        usage=SimpleNamespace(input_tokens=7, output_tokens=10, total_tokens=17),
    )
    fake = _FakeOpenAI(response)
    monkeypatch.setattr(openai, "OpenAI", lambda **_kwargs: fake)

    with caplog.at_level("WARNING", logger="llm_client"):
        result = llm_client._chat_openai(
            [], "gpt-5.6-sol", 10, 0.0, "token", 30
        )

    assert result == output_text
    assert "max_output_tokens; returning available text" in caplog.text


def test_gpt_5_6_other_incomplete_response_still_raises(monkeypatch):
    import openai

    response = SimpleNamespace(
        status="incomplete",
        incomplete_details=SimpleNamespace(reason="unknown"),
    )
    fake = _FakeOpenAI(response)
    monkeypatch.setattr(openai, "OpenAI", lambda **_kwargs: fake)

    with pytest.raises(RuntimeError, match="unknown"):
        llm_client._chat_openai([], "gpt-5.6-sol", 10, 0.0, "token", 30)


def test_non_gpt_5_6_keeps_chat_completions(monkeypatch):
    import openai

    fake = _FakeOpenAI(_completed_response())
    monkeypatch.setattr(openai, "OpenAI", lambda **_kwargs: fake)

    result = llm_client._chat_openai(
        [{"role": "user", "content": "hello"}],
        "gpt-4o-mini",
        88,
        0.4,
        "test-token",
        45,
    )

    assert result == "legacy reply"
    assert fake.responses.last_kwargs is None
    assert fake.chat.completions.last_kwargs == {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "hello"}],
        "max_tokens": 88,
        "temperature": 0.4,
    }


@pytest.mark.parametrize(
    "model",
    ["gpt-5", "gpt-5-mini", "o1", "o3", "o4-mini", "openai/o4-mini", "openai/gpt-5"],
)
def test_reasoning_family_sends_max_completion_tokens_without_temperature(
    monkeypatch, model
):
    """The reasoning families answer HTTP 400 to the legacy `max_tokens` param
    and to any non-default temperature. gpt-5.6 escapes this via the Responses
    API above; everything else in the family stays on chat/completions and has
    to be sent the modern parameter names."""
    import openai

    fake = _FakeOpenAI(_completed_response())
    monkeypatch.setattr(openai, "OpenAI", lambda **_kwargs: fake)

    result = llm_client._chat_openai(
        [{"role": "user", "content": "hello"}],
        model,
        8800,
        0.4,
        "test-token",
        45,
    )

    assert result == "legacy reply"
    assert fake.responses.last_kwargs is None
    assert fake.chat.completions.last_kwargs == {
        "model": model,
        "messages": [{"role": "user", "content": "hello"}],
        "max_completion_tokens": 8800,
    }


def test_native_anthropic_request_shape_is_preserved(monkeypatch):
    created = []
    calls = []

    class _FakeMessages:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text="claude reply")],
                usage=SimpleNamespace(input_tokens=6, output_tokens=3),
            )

    class _FakeAnthropic:
        def __init__(self, **kwargs):
            created.append(kwargs)
            self.messages = _FakeMessages()

    monkeypatch.setitem(
        sys.modules, "anthropic", SimpleNamespace(Anthropic=_FakeAnthropic)
    )
    llm_client.reset_call_log()

    result = llm_client._chat_anthropic(
        [
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "previous reply"},
        ],
        "claude-opus-4-8",
        222,
        0.7,
        "anthropic-token",
        45,
    )

    assert result == "claude reply"
    assert created == [{"api_key": "anthropic-token", "timeout": 45}]
    assert calls == [
        {
            "model": "claude-opus-4-8",
            "max_tokens": 222,
            "messages": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "previous reply"},
            ],
            "system": "system prompt",
        }
    ]
    assert llm_client.call_log_summary()["calls"] == 1
    assert llm_client.call_log_summary()["total_tokens"] == 9


def test_judge_provider_is_independent_from_arm_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("ADHERENCE_JUDGE_MODEL", "claude-opus-4-8")
    monkeypatch.delenv("ADHERENCE_JUDGE_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_CALL_ROLE", raising=False)

    assert llm_client._provider_for("gpt-5.6-sol") == "openai"
    assert llm_client._provider_for("claude-opus-4-8") == "anthropic"

    monkeypatch.setenv("ADHERENCE_JUDGE_MODEL", "gpt-5.6-sol")
    assert llm_client._provider_for("gpt-5.6-sol") == "openai"


def test_call_role_disambiguates_same_model_arm_and_judge(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ADHERENCE_JUDGE_MODEL", "claude-opus-4-8")
    monkeypatch.setenv("ADHERENCE_JUDGE_PROVIDER", "openai")

    monkeypatch.setenv("LLM_CALL_ROLE", "arm")
    assert llm_client._provider_for("claude-opus-4-8") == "anthropic"

    monkeypatch.setenv("LLM_CALL_ROLE", "judge")
    assert llm_client._provider_for("claude-opus-4-8") == "openai"


@pytest.mark.parametrize("model", ["gpt-5.6-luna", "o4-mini"])
def test_reasoning_family_budget_is_floored_for_one_word_judges(monkeypatch, model):
    """The chat verifiers ask the judge for a one-word label with max_tokens=16.
    A reasoning judge spends all 16 on reasoning and returns "", which the
    verifier records as a failed check. The budget is floored so the label
    still fits after the reasoning."""
    import openai

    fake = _FakeOpenAI(_completed_response(output_text="HELD"))
    monkeypatch.setattr(openai, "OpenAI", lambda **_kwargs: fake)

    llm_client._chat_openai(
        [{"role": "user", "content": "label?"}], model, 16, 0.0, "test-token", 45
    )

    sent = fake.responses.last_kwargs or fake.chat.completions.last_kwargs
    budget = sent.get("max_output_tokens") or sent.get("max_completion_tokens")
    assert budget == llm_client.REASONING_MIN_BUDGET


def test_non_reasoning_budget_is_not_floored(monkeypatch):
    import openai

    fake = _FakeOpenAI(_completed_response())
    monkeypatch.setattr(openai, "OpenAI", lambda **_kwargs: fake)

    llm_client._chat_openai(
        [{"role": "user", "content": "label?"}], "gpt-4o", 16, 0.0, "test-token", 45
    )

    assert fake.chat.completions.last_kwargs["max_tokens"] == 16


def test_screenshot_parts_are_translated_per_provider():
    import llm_client
    content = [{"type": "text", "text": "page"},
               {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,QUJD"}}]
    assert llm_client._anthropic_content(content) == [
        {"type": "text", "text": "page"},
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "QUJD"}}]
    assert llm_client._responses_input([{"role": "user", "content": content}]) == [
        {"role": "user", "content": [{"type": "input_text", "text": "page"},
                                     {"type": "input_image", "image_url": "data:image/jpeg;base64,QUJD"}]}]
    assert llm_client._gemini_parts(content) == [
        {"text": "page"}, {"inline_data": {"mime_type": "image/jpeg", "data": b"ABC"}}]
    # plain string content is untouched everywhere
    assert llm_client._anthropic_content("hi") == "hi"
    assert llm_client._responses_input([{"role": "user", "content": "hi"}]) == [{"role": "user", "content": "hi"}]
