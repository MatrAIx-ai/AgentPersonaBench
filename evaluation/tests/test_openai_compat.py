"""Routing tests for the OpenAI-compatible providers (Qwen/DashScope, GLM/Z.ai).

These assert the thing that actually broke before: that a call lands on the right
host with the right key, and that the arm and the judge can be routed apart.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

import llm_client
import openai_compat

REPO = Path(__file__).resolve().parents[2]

# Load LiteLLM's provider table before any test swaps a fake `openai` into
# sys.modules: litellm imports openai lazily, and would otherwise pick up the
# stand-in the routing fixtures install and fail on it. Ordering, not pricing.
try:  # pragma: no cover - telemetry only
    import litellm  # noqa: F401
except Exception:  # noqa: BLE001
    litellm = None


# --- registry ----------------------------------------------------------------
def test_bare_model_ids_route_to_their_provider():
    assert openai_compat.provider_for_model("glm-5.3") == "zai"
    assert openai_compat.provider_for_model("qwen3-max") == "dashscope"
    assert openai_compat.provider_for_model("deepseek-flash") == "deepseek"
    assert openai_compat.provider_for_model("deepseek-v4-pro") == "deepseek"
    assert openai_compat.provider_for_model("claude-opus-4-8") == ""


@pytest.mark.parametrize(
    "model,expected",
    [("glm-5.3", "zai"), ("qwen-plus", "dashscope"),
     ("deepseek-flash", "deepseek"),
     ("deepseek-v4-pro", "deepseek"),
     ("gpt-5.6", "openai"), ("gemini-2.5-flash", "gemini"),
     ("claude-opus-4-8", "anthropic")],
)
def test_inferred_provider_covers_every_arm_family(model, expected):
    assert llm_client._inferred_provider(model) == expected


def test_every_registered_provider_has_a_backend_and_key_env():
    for name in openai_compat.REGISTRY:
        assert name in llm_client._BACKENDS
        assert llm_client._KEY_ENV[name]


def test_base_url_precedence_is_role_then_provider_env_then_default():
    default = openai_compat.base_url_for("zai", {})
    assert default == "https://api.z.ai/api/paas/v4"
    assert openai_compat.base_url_for("zai", {"ZAI_API_BASE": "http://vendor/v1"}) == "http://vendor/v1"
    assert openai_compat.base_url_for(
        "zai", {"LLM_CALL_ROLE": "arm", "LLM_BASE_URL": "http://gw/v1",
                "ZAI_API_BASE": "http://vendor/v1"}) == "http://gw/v1"


def test_arm_and_judge_resolve_to_different_endpoints():
    """The reason this registry exists: one global OPENAI_BASE_URL cannot do this."""
    env = {"LLM_BASE_URL": "http://arm/v1", "ADHERENCE_JUDGE_BASE_URL": "http://judge/v1"}
    assert openai_compat.base_url_for("zai", {**env, "LLM_CALL_ROLE": "arm"}) == "http://arm/v1"
    assert openai_compat.base_url_for("zai", {**env, "LLM_CALL_ROLE": "judge"}) == "http://judge/v1"


# --- the call actually reaches the right endpoint ----------------------------
class _Recorder:
    """Stands in for the openai SDK and records how the client was constructed."""

    def __init__(self):
        self.client_kwargs = None
        self.create_kwargs = None
        self.used_responses_api = False

    def OpenAI(self, **kwargs):
        self.client_kwargs = kwargs
        outer = self

        class _Completions:
            def create(self, **kw):
                outer.create_kwargs = kw
                usage = types.SimpleNamespace(prompt_tokens=3, completion_tokens=5, total_tokens=8)
                message = types.SimpleNamespace(content="ok")
                return types.SimpleNamespace(
                    choices=[types.SimpleNamespace(message=message)], usage=usage)

        class _Responses:
            def create(self, **kw):
                outer.used_responses_api = True
                raise AssertionError("must not use the Responses API here")

        return types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=_Completions()),
            responses=_Responses())


@pytest.fixture
def recorder(monkeypatch):
    rec = _Recorder()
    monkeypatch.setitem(sys.modules, "openai", rec)
    llm_client.reset_call_log()
    for var in ("LLM_PROVIDER", "LLM_CALL_ROLE", "LLM_BASE_URL",
                "ADHERENCE_JUDGE_BASE_URL", "ADHERENCE_JUDGE_MODEL",
                "ADHERENCE_JUDGE_PROVIDER", "ZAI_API_BASE", "DASHSCOPE_API_BASE"):
        monkeypatch.delenv(var, raising=False)
    return rec


def test_glm_call_goes_to_zai_not_openai(recorder, monkeypatch):
    monkeypatch.setenv("ZAI_API_KEY", "zai-key")
    out = llm_client.chat([{"role": "user", "content": "hi"}], model="glm-5.3")
    assert out == "ok"
    assert recorder.client_kwargs["base_url"] == "https://api.z.ai/api/paas/v4"
    assert recorder.client_kwargs["api_key"] == "zai-key"
    assert recorder.create_kwargs["model"] == "glm-5.3"
    assert llm_client.call_log_summary()["total_tokens"] == 8


def test_qwen_call_goes_to_dashscope(recorder, monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "ds-key")
    llm_client.chat([{"role": "user", "content": "hi"}], model="qwen3-max")
    assert recorder.client_kwargs["base_url"].startswith("https://dashscope.aliyuncs.com")
    assert recorder.client_kwargs["api_key"] == "ds-key"


def test_deepseek_call_goes_to_deepseek(recorder, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")
    llm_client.chat([{"role": "user", "content": "hi"}], model="deepseek-flash")
    llm_client.chat([{"role": "user", "content": "hi"}], model="deepseek-v4-pro")
    assert recorder.client_kwargs["base_url"] == "https://api.deepseek.com"
    assert recorder.client_kwargs["api_key"] == "deepseek-key"


def test_compatible_provider_never_uses_the_responses_api(recorder, monkeypatch):
    """A non-OpenAI endpoint has no /responses; a Responses-family model name on a
    compatible provider must still go to /chat/completions."""
    monkeypatch.setenv("ZAI_API_KEY", "zai-key")
    monkeypatch.setenv("LLM_PROVIDER", "zai")
    llm_client.chat([{"role": "user", "content": "hi"}], model="gpt-5.6")
    assert recorder.used_responses_api is False
    assert recorder.create_kwargs["model"] == "gpt-5.6"


def test_openai_proper_keeps_the_sdk_default_base_url(recorder, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "oai-key")
    llm_client.chat([{"role": "user", "content": "hi"}], model="gpt-4o-mini")
    assert "base_url" not in recorder.client_kwargs


def test_missing_key_names_the_env_var_to_set(monkeypatch):
    for var in openai_compat.key_env_names("zai"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(RuntimeError, match="ZAI_API_KEY"):
        llm_client.load_token("zai")


# --- the chat persona simulator ----------------------------------------------
def test_persona_sim_bare_glm_id_no_longer_falls_through_to_anthropic(monkeypatch):
    from playground import model_client

    monkeypatch.setenv("ZAI_API_KEY", "zai-key")
    monkeypatch.setenv("LLM_PROVIDER", "zai")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = model_client.build_json_client("glm-5.3")
    assert not isinstance(client, model_client.AnthropicJSONClient)
    assert client.model == "glm-5.3"


def test_persona_sim_still_defaults_to_anthropic_for_claude(monkeypatch):
    from playground import model_client

    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    client = model_client.build_json_client("claude-opus-4-8")
    assert isinstance(client, model_client.AnthropicJSONClient)


# --- the chat persona simulator drives turns through a TOOL client, not the JSON
# --- client; both dispatchers have to resolve the provider or chat dies at setup
def test_both_persona_client_builders_route_compatible_providers(monkeypatch):
    """Regression: build_tool_step_client was missed when build_json_client was
    fixed, so every chat task died in <1s with 'ANTHROPIC_API_KEY ... is required
    for persona model glm-5.3' before making a single request."""
    pytest.importorskip("openai")
    from playground.model_client import build_json_client
    from playground.user_sim.tool_client import (
        AnthropicToolStepClient,
        build_tool_step_client,
    )

    monkeypatch.setenv("LLM_PROVIDER", "zai")
    monkeypatch.setenv("ZAI_API_KEY", "zai-key")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)

    tool_client = build_tool_step_client("glm-5.3")
    assert not isinstance(tool_client, AnthropicToolStepClient)
    assert "api.z.ai" in str(tool_client._client.base_url)
    assert tool_client.use_responses_api is False

    json_client = build_json_client("glm-5.3")
    assert "api.z.ai" in str(json_client._client.base_url)


def test_tool_client_routes_qwen_to_dashscope(monkeypatch):
    pytest.importorskip("openai")
    from playground.user_sim.tool_client import build_tool_step_client

    monkeypatch.setenv("LLM_PROVIDER", "dashscope")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "ds-key")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = build_tool_step_client("qwen3-max")
    assert "dashscope.aliyuncs.com" in str(client._client.base_url)


def test_tool_client_still_uses_anthropic_for_claude(monkeypatch):
    from playground.user_sim.tool_client import (
        AnthropicToolStepClient,
        build_tool_step_client,
    )

    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert isinstance(build_tool_step_client("claude-opus-4-8"), AnthropicToolStepClient)


def test_tool_client_leaves_plain_openai_to_the_sdk(monkeypatch):
    """provider "openai" must not be given a base_url here — the SDK's own default
    (or OPENAI_BASE_URL) has to keep winning."""
    pytest.importorskip("openai")
    from playground.user_sim.tool_client import build_tool_step_client

    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "oai-key")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    client = build_tool_step_client("gpt-4o-mini")
    assert "api.openai.com" in str(client._client.base_url)


# --- the benchmark judge ------------------------------------------------------
def test_judge_default_comes_from_the_benchmark_config():
    import judge

    j = judge.resolve({}, {})
    assert j.model == "gpt-5.6-luna"
    assert j.provider == "openai"
    assert j.source == "configs/judge.json"


def test_judge_precedence_env_beats_arm_beats_benchmark():
    import judge

    arm = {"judge_model": "claude-opus-4-8"}
    assert judge.resolve(arm, {}).model == "claude-opus-4-8"
    assert judge.resolve(arm, {"ADHERENCE_JUDGE_MODEL": "glm-5.3-flash"}).model == "glm-5.3-flash"


def test_judge_provider_is_inferred_only_when_unnamed():
    import judge

    assert judge.resolve({}, {"ADHERENCE_JUDGE_MODEL": "qwen3.8-flash"}).provider == "dashscope"
    assert judge.resolve({}, {"ADHERENCE_JUDGE_MODEL": "glm-5.3-flash"}).provider == "zai"
    assert judge.resolve({}, {"ADHERENCE_JUDGE_MODEL": "claude-opus-4-8"}).provider == "anthropic"
    # an explicit choice is never second-guessed
    forced = judge.resolve({}, {"ADHERENCE_JUDGE_MODEL": "claude-opus-4-8",
                                "ADHERENCE_JUDGE_PROVIDER": "openrouter"})
    assert forced.provider == "openrouter"


def test_judge_and_arm_stay_independently_routable(monkeypatch):
    """The point of a benchmark-wide judge: the arm can move, the judge cannot."""
    import importlib
    import llm_client
    import openai_compat

    for var in ("LLM_PROVIDER", "LLM_CALL_ROLE", "ADHERENCE_JUDGE_PROVIDER",
                "ADHERENCE_JUDGE_BASE_URL", "LLM_BASE_URL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "dashscope")
    monkeypatch.setenv("ADHERENCE_JUDGE_MODEL", "gpt-5.6-luna")
    monkeypatch.setenv("ADHERENCE_JUDGE_PROVIDER", "openai")
    importlib.reload(openai_compat)
    importlib.reload(llm_client)

    monkeypatch.setenv("LLM_CALL_ROLE", "arm")
    assert llm_client._provider_for("qwen3.8-flash") == "dashscope"
    monkeypatch.setenv("LLM_CALL_ROLE", "judge")
    assert llm_client._provider_for("gpt-5.6-luna") == "openai"


# --- cost ---------------------------------------------------------------------
def test_pricing_uses_the_provider_qualified_id():
    """LiteLLM prices zai/glm-5.3-flash but not the bare id the arm config holds."""
    pytest.importorskip("litellm")
    import pricing

    if pricing.rates_for("gpt-4o", "openai") is None:
        pytest.skip("this litellm install cannot price anything")
    assert pricing.rates_for("glm-5.3-flash", "zai") is not None
    assert pricing.cost_usd("glm-5.3-flash", 1_000_000, 0, "zai") > 0


def test_pricing_returns_none_rather_than_zero_for_an_unknown_model():
    """A silent $0.00 reads as 'this arm was free', which is worse than a blank."""
    pytest.importorskip("litellm")
    import pricing

    assert pricing.cost_usd("no-such-model-xyz", 1000, 1000, "openai") is None


def test_pricing_accepts_a_per_arm_override():
    import pricing

    cost = pricing.cost_usd("no-such-model-xyz", 1_000_000, 1_000_000, "dashscope",
                            {"price_per_mtok": {"input": 0.3, "output": 0.9}})
    assert cost == pytest.approx(1.2)


def test_report_prices_recorded_tokens_when_the_runtime_did_not():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "report_suite", REPO / "evaluation" / "report_suite.py")
    report = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(report)

    envelope = {"model": "glm-5.3-flash", "provider": "zai"}
    usage = {"prompt_tokens": 6611, "completion_tokens": 732}
    assert report.resolved_cost(usage, envelope) > 0
    # a recorded cost wins over re-deriving it
    assert report.resolved_cost({**usage, "cost_usd": 0.5}, envelope) == 0.5
    # no tokens, no cost - never a zero
    assert report.resolved_cost({}, envelope) is None


def test_report_labels_a_partial_cost_total():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "report_suite", REPO / "evaluation" / "report_suite.py")
    report = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(report)

    assert report.fmt_cost([{"cost_usd": 0.01}, {"cost_usd": 0.02}]) == "$0.0300"
    assert "1/2 priced" in report.fmt_cost([{"cost_usd": 0.01}, {"cost_usd": None}])
    assert report.fmt_cost([{"cost_usd": 0.0}]) == "—"


# --- token capture ------------------------------------------------------------
def test_persona_sim_and_bot_share_one_call_log():
    """Chat spends on two paths — the simulator's client and the bot via
    llm_client — and a trial's total is only right if both land in one log."""
    import time as _time

    import usage

    usage.reset()
    usage.record_response(
        "glm-5.3-flash",
        types.SimpleNamespace(usage=types.SimpleNamespace(
            prompt_tokens=4000, completion_tokens=300)),
        source="persona-sim")
    llm_client._record("glm-5.3-flash", 1500, 200, 1700, _time.time())

    total = usage.summary()
    assert total["calls"] == 2
    assert total["total_tokens"] == 6000
    # llm_client's own aggregate keeps working over the shared list
    assert llm_client.call_log_summary()["total_tokens"] == 6000
    usage.reset()


def test_usage_skips_a_response_with_no_counts():
    """A missing usage block must not be recorded as zero: zero would understate
    the total and then be priced as free."""
    import usage

    usage.reset()
    usage.record_response("m", types.SimpleNamespace(usage=None))
    usage.record_response("m", types.SimpleNamespace(
        usage=types.SimpleNamespace(prompt_tokens=0, completion_tokens=0)))
    assert usage.summary() == {}
    usage.reset()


def test_usage_reads_both_the_chat_and_responses_shapes():
    import usage

    usage.reset()
    usage.record_response("m", {"usage": {"input_tokens": 7, "output_tokens": 3}})
    usage.record_response("m", types.SimpleNamespace(
        usage=types.SimpleNamespace(prompt_tokens=10, completion_tokens=5)))
    assert usage.summary()["total_tokens"] == 25
    usage.reset()


def test_unknown_latency_is_omitted_not_stored_as_none():
    """llm_client sums this list with `.get("latency_s", 0.0)`; a present None
    makes that raise instead of defaulting."""
    import usage

    usage.reset()
    usage.record("m", 10, 5)
    assert "latency_s" not in usage.CALL_LOG[0]
    assert llm_client.call_log_summary()["latency_s"] == 0.0
    usage.reset()


def test_cached_input_is_billed_at_the_cache_rate():
    """42% of a recorded Qwen run's prompt tokens were cache hits, and GLM reads a
    cached token at a fifth of a fresh one — charging them all as fresh overstates
    a run by tens of percent."""
    pytest.importorskip("litellm")
    import pricing

    if pricing.rates_for("glm-5.3-flash", "zai") is None:
        pytest.skip("this litellm install cannot price anything")
    fresh_only = pricing.cost_usd("glm-5.3-flash", 1_000_000, 0, "zai")
    all_cached = pricing.cost_usd("glm-5.3-flash", 1_000_000, 0, "zai",
                                  cached_tokens=1_000_000)
    assert 0 < all_cached < fresh_only
    # cached is a subset of prompt, never additive, and never negative
    assert pricing.cost_usd("glm-5.3-flash", 100, 0, "zai", cached_tokens=999) == all_cached / 10_000


def test_config_override_can_declare_a_cache_rate():
    import pricing

    rates = {"price_per_mtok": {"input": 1.0, "cached_input": 0.1, "output": 2.0}}
    assert pricing.cost_usd("x", 1_000_000, 0, "", rates) == pytest.approx(1.0)
    assert pricing.cost_usd("x", 1_000_000, 0, "", rates, cached_tokens=1_000_000) == pytest.approx(0.1)
    # without cached_input, cached tokens bill as fresh
    plain = {"price_per_mtok": {"input": 1.0, "output": 2.0}}
    assert pricing.cost_usd("x", 1_000_000, 0, "", plain, cached_tokens=1_000_000) == pytest.approx(1.0)
