"""The suite's --effort must reach every vendor, on every surface, as a request field.

Before this, only the OpenAI text path sent it: Claude text calls carried no
thinking config (Opus 4.8 / Haiku 4.5 did not think, Opus 5 thought at its
default high), Gemini text and computer-use ran at the model default (high),
and the OpenAI computer-use loop sent no reasoning object. These tests pin the
request each path builds, without any network.
"""
from __future__ import annotations

import json
import sys
import threading
import types
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from playground import reasoning


# --- the mapping -------------------------------------------------------------
@pytest.mark.parametrize("model", ["claude-opus-4-8", "claude-opus-5", "claude-sonnet-5"])
def test_adaptive_claude_models_get_adaptive_thinking_and_effort(model):
    fields, max_tokens = reasoning.claude_thinking(model, "medium", 1200)
    assert fields == {"thinking": {"type": "adaptive"}, "output_config": {"effort": "medium"}}
    # opus-4-8 ships max_tokens=1200; thinking shares it, so it must grow.
    assert max_tokens == reasoning.CLAUDE_THINKING_MIN_MAX_TOKENS


def test_haiku_gets_a_budget_and_no_effort_field():
    fields, max_tokens = reasoning.claude_thinking("claude-haiku-4-5-20251001", "medium", 1200)
    assert fields == {"thinking": {"type": "enabled", "budget_tokens": 2048}}
    assert "output_config" not in fields          # effort 400s on Haiku 4.5
    assert max_tokens > 2048                      # budget_tokens < max_tokens


@pytest.mark.parametrize("effort", ["", None, "turbo"])
def test_unset_or_unknown_effort_changes_nothing(effort):
    assert reasoning.claude_thinking("claude-opus-4-8", effort, 1200) == ({}, 1200)
    assert reasoning.gemini_thinking_level("gemini-3.7-flash", effort) is None
    assert reasoning.openai_reasoning(effort) is None


def test_gemini_level_only_for_gemini_3():
    assert reasoning.gemini_thinking_level("gemini-3.7-flash", "medium") == "medium"
    assert reasoning.gemini_thinking_level("gemini/gemini-3.8-flash", "low") == "low"
    assert reasoning.gemini_thinking_level("gemini-2.5-flash", "medium") is None


# --- llm_client, Anthropic: the request that actually leaves the process -----
class _Capture(BaseHTTPRequestHandler):
    bodies: list = []

    def do_POST(self):  # noqa: N802
        n = int(self.headers.get("content-length", 0))
        _Capture.bodies.append(json.loads(self.rfile.read(n)))
        reply = {"id": "msg_1", "type": "message", "role": "assistant", "model": "m",
                 "content": [{"type": "thinking", "thinking": "", "signature": "s"},
                             {"type": "text", "text": "ok"}],
                 "stop_reason": "end_turn", "stop_sequence": None,
                 "usage": {"input_tokens": 3, "output_tokens": 5}}
        data = json.dumps(reply).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):  # quiet
        pass


@pytest.fixture
def anthropic_stub(monkeypatch):
    srv = HTTPServer(("127.0.0.1", 0), _Capture)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setenv("ANTHROPIC_BASE_URL", f"http://127.0.0.1:{srv.server_port}")
    _Capture.bodies = []
    yield _Capture.bodies
    srv.shutdown()


def test_llm_client_sends_claude_thinking_at_suite_effort(anthropic_stub, monkeypatch):
    pytest.importorskip("anthropic")
    import llm_client

    monkeypatch.setenv("LLM_REASONING_EFFORT", "medium")
    out = llm_client._chat_anthropic([{"role": "system", "content": "persona"},
                                      {"role": "user", "content": "pick"}],
                                     "claude-opus-4-8", 1200, 0.3, "k", 30)
    assert out == "ok"                      # thinking blocks are not returned as text
    body = anthropic_stub[-1]
    assert body["thinking"] == {"type": "adaptive"}
    assert body["output_config"] == {"effort": "medium"}
    assert body["max_tokens"] >= 16000
    assert "temperature" not in body


def test_llm_client_without_effort_sends_no_thinking(anthropic_stub, monkeypatch):
    pytest.importorskip("anthropic")
    import llm_client

    monkeypatch.delenv("LLM_REASONING_EFFORT", raising=False)
    llm_client._chat_anthropic([{"role": "user", "content": "pick"}],
                               "claude-opus-4-8", 1200, 0.3, "k", 30)
    body = anthropic_stub[-1]
    assert "thinking" not in body and "output_config" not in body
    assert body["max_tokens"] == 1200


# --- llm_client, Gemini: the config handed to generate_content --------------
def test_llm_client_sends_gemini_thinking_level(monkeypatch):
    pytest.importorskip("google.genai")
    import llm_client
    from google import genai

    seen = {}

    class _Models:
        def generate_content(self, model, contents, config):
            seen["config"] = config
            return types.SimpleNamespace(text="ok", usage_metadata=None)

    monkeypatch.setattr(genai, "Client", lambda **kw: types.SimpleNamespace(models=_Models()))
    monkeypatch.setenv("LLM_REASONING_EFFORT", "medium")
    llm_client._chat_gemini([{"role": "user", "content": "pick"}],
                            "gemini-3.7-flash", 1024, 0.3, "k", 30)
    assert seen["config"].thinking_config.thinking_level.lower() == "medium"
    # a short caller budget is floored like the OpenAI reasoning path
    assert seen["config"].max_output_tokens >= llm_client.REASONING_MIN_BUDGET


# --- computer-use providers ---------------------------------------------------
def _agent(model, effort):
    geo = types.SimpleNamespace(desktop_width=1280, desktop_height=800)
    return types.SimpleNamespace(
        _model_name=model, _desktop_geometry=geo, _aws_region_name=None,
        _identity_prompt=None, _gemini_auto_ack_safety=False,
        _llm=types.SimpleNamespace(_reasoning_effort=effort))


def test_gemini_computer_use_gets_thinking_level(monkeypatch):
    pytest.importorskip("google.genai")
    from harbor.agents.computer_1.providers import gemini as g

    monkeypatch.setattr(g.genai, "Client", lambda **kw: object())
    p = g.GeminiProvider.from_agent(_agent("gemini-3.7-flash", "medium"))
    assert p._generate_config.thinking_config.thinking_level.lower() == "medium"
    assert p._generate_config.max_output_tokens >= 16384


def test_openai_computer_use_sends_reasoning(monkeypatch):
    pytest.importorskip("openai")
    from harbor.agents.computer_1.providers import openai as o

    monkeypatch.setattr(o, "_make_openai_client", lambda: object())
    p = o.OpenAIComputerUseProvider.from_agent(_agent("gpt-6-astra", "medium"))
    assert p._reasoning == {"reasoning": {"effort": "medium"}}
    assert o.OpenAIComputerUseProvider.from_agent(_agent("gpt-6-astra", None))._reasoning == {}


def test_anthropic_computer_use_sends_thinking(monkeypatch):
    pytest.importorskip("anthropic")
    from harbor.agents.computer_1.providers import anthropic as a

    monkeypatch.setattr(a, "_make_anthropic_client", lambda cls: object())
    p = a.AnthropicProvider.from_agent(_agent("claude-opus-4-8", "medium"))
    assert p._thinking == {"thinking": {"type": "adaptive"}, "output_config": {"effort": "medium"}}
    assert p._max_tokens >= 16000
    h = a.AnthropicProvider.from_agent(_agent("claude-haiku-4-5-20251001", "medium"))
    assert h._thinking == {"thinking": {"type": "enabled", "budget_tokens": 2048}}
