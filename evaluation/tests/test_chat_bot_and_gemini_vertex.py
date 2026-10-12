"""The chat bot is a fixed model routed independently of the arm, and Gemini
reaches the chat persona clients through Vertex AI when asked to."""
from __future__ import annotations

import sys
import types

import chat_harness
import llm_client
from playground import model_client


def test_bot_is_a_fixed_model_routed_like_the_judge(monkeypatch):
    monkeypatch.delenv("APB_CHAT_BOT_MODEL", raising=False)
    monkeypatch.setenv("ADHERENCE_JUDGE_MODEL", "gpt-5.6-luna")
    assert chat_harness._bot_model("gemini-3.7-flash") == ("gemini-3.7-flash", {})  # default: the arm
    monkeypatch.setenv("APB_CHAT_BOT_MODEL", "gpt-5.6-luna")
    assert chat_harness._bot_model("gemini-3.7-flash") == ("gpt-5.6-luna", {"role": "judge"})
    monkeypatch.setenv("APB_CHAT_BOT_MODEL", "gpt-6-sol")
    assert chat_harness._bot_model("gemini-3.7-flash") == ("gpt-6-sol", {"role": "bot"})
    monkeypatch.setenv("APB_CHAT_BOT_MODEL", "arm")
    assert chat_harness._bot_model("gemini-3.7-flash") == ("gemini-3.7-flash", {})


def test_bot_call_ignores_the_arm_provider(monkeypatch):
    seen = {}
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_CALL_ROLE", "arm")
    monkeypatch.setenv("ADHERENCE_JUDGE_MODEL", "gpt-5.6-luna")
    monkeypatch.setenv("ADHERENCE_JUDGE_PROVIDER", "azure")

    def fake(messages, model, *a, **k):
        seen["provider"] = llm_client._provider_for(model)
        seen["role"] = llm_client.os.environ["LLM_CALL_ROLE"]
        return "ok"
    monkeypatch.setitem(llm_client._BACKENDS, "azure", fake)
    monkeypatch.setitem(llm_client._BACKENDS, "gemini", lambda *a, **k: "WRONG")
    monkeypatch.setattr(llm_client, "load_token", lambda p=None: "k")
    assert llm_client.chat([{"role": "user", "content": "hi"}], model="gpt-5.6-luna", call_role="judge") == "ok"
    assert seen == {"provider": "azure", "role": "judge"}
    assert llm_client.os.environ["LLM_CALL_ROLE"] == "arm"  # restored


def test_gemini_persona_client_uses_vertex_openai_endpoint(monkeypatch):
    class Creds:
        token = "tok"
        def refresh(self, request):
            pass
    auth = types.ModuleType("google.auth")
    auth.default = lambda scopes=None: (Creds(), "p")
    transport = types.ModuleType("google.auth.transport")
    requests = types.ModuleType("google.auth.transport.requests")
    requests.Request = object
    monkeypatch.setitem(sys.modules, "google.auth", auth)
    monkeypatch.setitem(sys.modules, "google.auth.transport", transport)
    monkeypatch.setitem(sys.modules, "google.auth.transport.requests", requests)
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.delenv("GOOGLE_CLOUD_LOCATION", raising=False)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "proj")
    kw = model_client.gemini_openai_client_kwargs("gemini-3.7-flash")
    assert kw == {"model": "google/gemini-3.7-flash", "api_key": "tok",
                  "base_url": "https://aiplatform.googleapis.com/v1/projects/proj/locations/global/endpoints/openapi"}
