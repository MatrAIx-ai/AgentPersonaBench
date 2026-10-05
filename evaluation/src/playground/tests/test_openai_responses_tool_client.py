from __future__ import annotations

from types import SimpleNamespace

import pytest

from matraix.persona_agent_context import CHATBOT_MAX_OUTPUT_TOKENS
from playground.user_sim.tool_client import OpenAIToolStepClient
from playground.user_sim.tools import ToolCall


class _FakeResponses:
    def __init__(self, response):
        self.response = response
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return self.response


class _FakeClient:
    def __init__(self, response):
        self.responses = _FakeResponses(response)
        self.chat = SimpleNamespace(completions=SimpleNamespace(last_kwargs=None))


def test_responses_tool_request_and_calls_are_mapped_in_order(monkeypatch):
    response = SimpleNamespace(
        status="completed",
        output_text="",
        output=[
            SimpleNamespace(type="reasoning"),
            SimpleNamespace(
                type="function_call",
                name="send_message",
                arguments='{"message":"hello"}',
            ),
            SimpleNamespace(
                type="function_call",
                name="end_conversation",
                arguments='{"reason":"satisfied"}',
            ),
        ],
    )
    fake = _FakeClient(response)
    monkeypatch.delenv("LLM_REASONING_EFFORT", raising=False)
    client = OpenAIToolStepClient(model="gpt-5.6-sol", client=fake)
    messages = [
        {"role": "system", "content": "persona"},
        {"role": "user", "content": "observation"},
    ]

    assert client.complete_with_tools(messages) == [
        ToolCall("send_message", {"message": "hello"}),
        ToolCall("end_conversation", {"reason": "satisfied"}),
    ]

    kwargs = fake.responses.last_kwargs
    assert kwargs["model"] == "gpt-5.6-sol"
    assert kwargs["input"] == messages
    assert kwargs["tool_choice"] == "auto"
    assert kwargs["max_output_tokens"] == CHATBOT_MAX_OUTPUT_TOKENS
    assert kwargs["store"] is False
    assert "messages" not in kwargs
    assert "temperature" not in kwargs
    assert "reasoning" not in kwargs
    assert [tool["name"] for tool in kwargs["tools"]] == [
        "send_message",
        "end_conversation",
    ]
    assert all(tool["type"] == "function" for tool in kwargs["tools"])
    assert all(tool["strict"] is False for tool in kwargs["tools"])
    assert all("function" not in tool for tool in kwargs["tools"])


def test_responses_tool_request_passes_explicit_reasoning_effort(monkeypatch):
    response = SimpleNamespace(
        status="completed",
        output_text="plain reply",
        output=[],
    )
    fake = _FakeClient(response)
    monkeypatch.setenv("LLM_REASONING_EFFORT", "xhigh")

    calls = OpenAIToolStepClient("gpt-5.6", client=fake).complete_with_tools([])

    assert calls == [ToolCall("send_message", {"message": "plain reply"})]
    assert fake.responses.last_kwargs["reasoning"] == {"effort": "xhigh"}


def test_responses_tool_text_uses_nested_output_fallback(monkeypatch):
    response = {
        "status": "completed",
        "output_text": "",
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": "fallback reply"}],
            }
        ],
    }
    fake = _FakeClient(response)
    monkeypatch.delenv("LLM_REASONING_EFFORT", raising=False)

    calls = OpenAIToolStepClient("gpt-5.6-sol", client=fake).complete_with_tools([])

    assert calls == [ToolCall("send_message", {"message": "fallback reply"})]


def test_responses_tool_incomplete_output_raises(monkeypatch):
    response = SimpleNamespace(
        status="incomplete",
        incomplete_details=SimpleNamespace(reason="max_output_tokens"),
    )
    fake = _FakeClient(response)
    monkeypatch.delenv("LLM_REASONING_EFFORT", raising=False)

    with pytest.raises(RuntimeError, match="max_output_tokens"):
        OpenAIToolStepClient("gpt-5.6-sol", client=fake).complete_with_tools([])


def test_non_gpt_5_6_client_keeps_chat_completions():
    fake = _FakeClient(SimpleNamespace())
    client = OpenAIToolStepClient("gpt-5.5", client=fake)

    assert client.use_responses_api is False
