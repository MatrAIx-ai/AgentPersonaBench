"""OpenAI-compatible provider registry — one place that knows key + base URL.

Several providers speak the OpenAI `/chat/completions` wire format and differ only
in where they live and which env var holds the key: Alibaba DashScope (Qwen), Z.ai
(GLM), OpenRouter, and any self-hosted vLLM / LiteLLM gateway. None of them needs a
new adapter, so registering them here keeps `llm_client` free of vendor branches.

Why a registry instead of "just export OPENAI_BASE_URL": that env var is global to
the process, so it forces the arm and the LLM judge onto the same endpoint. A run
that puts the arm on GLM while the judge stays on Claude — the normal shape of a
fair comparison — is impossible with one global. Each provider resolving its own
base URL keeps the two independent, exactly as `LLM_PROVIDER` /
`ADHERENCE_JUDGE_PROVIDER` already keep their backends independent.

Resolution order for a base URL, highest first:

1. the per-role override — `LLM_BASE_URL` for the arm, `ADHERENCE_JUDGE_BASE_URL`
   for the judge (exported by run_task.py from the arm config's `base_url` /
   `judge_base_url`);
2. the provider's own env vars (e.g. `DASHSCOPE_API_BASE`);
3. the provider's default endpoint.

An empty result means "let the SDK decide", which is what `openai` proper wants.
"""
from __future__ import annotations

import os
from typing import NamedTuple


class OpenAICompatibleProvider(NamedTuple):
    """A provider reachable through the OpenAI SDK."""

    name: str
    key_env: tuple[str, ...]
    base_url_env: tuple[str, ...]
    default_base_url: str = ""
    # Providers other than OpenAI itself do not implement the Responses API, so
    # the client must stay on /chat/completions even for a model whose name
    # matches OpenAI's Responses-only families.
    supports_responses_api: bool = False


REGISTRY: dict[str, OpenAICompatibleProvider] = {
    "openai": OpenAICompatibleProvider(
        name="openai",
        key_env=("OPENAI_API_KEY",),
        base_url_env=("OPENAI_BASE_URL", "OPENAI_API_BASE"),
        default_base_url="",  # the SDK's own default
        supports_responses_api=True,
    ),
    # Azure AI Foundry speaks the OpenAI wire format at /openai/v1, Responses
    # API included, but it is NOT openai: the key is a different key and the
    # endpoint is per-resource. Registering it separately is what keeps an Azure
    # ARM from colliding with an OpenAI JUDGE - both would otherwise read
    # OPENAI_API_KEY and the arm's deployment key would be sent to api.openai.com.
    "azure": OpenAICompatibleProvider(
        name="azure",
        key_env=("AZURE_API_KEY", "AZURE_OPENAI_API_KEY"),
        base_url_env=("AZURE_API_BASE", "AZURE_OPENAI_ENDPOINT"),
        default_base_url="",          # per-resource; the arm config pins it
        supports_responses_api=True,
    ),
    "dashscope": OpenAICompatibleProvider(
        name="dashscope",
        key_env=("DASHSCOPE_API_KEY",),
        base_url_env=("DASHSCOPE_API_BASE", "DASHSCOPE_BASE_URL"),
        default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    ),
    "zai": OpenAICompatibleProvider(
        name="zai",
        key_env=("ZAI_API_KEY", "GLM_API_KEY", "ZHIPU_API_KEY"),
        base_url_env=("ZAI_API_BASE", "ZAI_BASE_URL"),
        default_base_url="https://api.z.ai/api/paas/v4",
    ),
    "xai": OpenAICompatibleProvider(
        name="xai",
        key_env=("XAI_API_KEY", "GROK_API_KEY"),
        base_url_env=("XAI_API_BASE", "XAI_BASE_URL"),
        default_base_url="https://api.x.ai/v1",
    ),
    "openrouter": OpenAICompatibleProvider(
        name="openrouter",
        key_env=("OPENROUTER_API_KEY",),
        base_url_env=("OPENROUTER_API_BASE", "OPENROUTER_BASE_URL"),
        default_base_url="https://openrouter.ai/api/v1",
    ),
    "deepseek": OpenAICompatibleProvider(
        name="deepseek",
        key_env=("DEEPSEEK_API_KEY",),
        base_url_env=("DEEPSEEK_API_BASE", "DEEPSEEK_BASE_URL"),
        default_base_url="https://api.deepseek.com",
        supports_responses_api=False,
    ),
}

# Model-name prefixes that identify a provider when no LLM_PROVIDER is set, so an
# ad-hoc call with a bare id still routes correctly.
MODEL_PREFIXES: tuple[tuple[str, str], ...] = (
    ("qwen", "dashscope"),
    ("glm", "zai"),
    ("deepseek", "deepseek"),
    ("grok", "xai"),
)


def is_openai_compatible(provider: str | None) -> bool:
    return (provider or "").strip().lower() in REGISTRY


def get(provider: str) -> OpenAICompatibleProvider:
    key = (provider or "").strip().lower()
    if key not in REGISTRY:
        raise KeyError(f"not an OpenAI-compatible provider: {provider!r}")
    return REGISTRY[key]


def _role_override(env: dict | None = None) -> str:
    """The per-call-role base URL override, or ''.

    Mirrors llm_client's arm/judge split: run_task marks solve calls `arm` and
    verifier calls `judge`, so a suite can route the two to different endpoints.
    """
    scope = os.environ if env is None else env
    role = str(scope.get("LLM_CALL_ROLE", "")).strip().lower()
    if role == "judge":
        return str(scope.get("ADHERENCE_JUDGE_BASE_URL", "")).strip()
    if role == "arm":
        return str(scope.get("LLM_BASE_URL", "")).strip()
    # No role declared (a standalone verifier, a script): the arm override is the
    # only sensible reading, since that is the endpoint the operator configured.
    return str(scope.get("LLM_BASE_URL", "")).strip()


def base_url_for(provider: str, env: dict | None = None) -> str:
    """Resolve the base URL for a provider. '' means 'SDK default'."""
    scope = os.environ if env is None else env
    override = _role_override(scope)
    if override:
        return override
    spec = get(provider)
    for name in spec.base_url_env:
        value = str(scope.get(name, "")).strip()
        if value:
            return value
    return spec.default_base_url


def explicit_base_url_for(provider: str, env: dict | None = None) -> str:
    """The base URL an operator actually configured, or '' if none.

    Unlike :func:`base_url_for` this never falls back to the provider's built-in
    endpoint. Callers that hand the model to a client which already knows the
    provider natively (LiteLLM, say) must only override the endpoint when it was
    asked for - otherwise a private or regional deployment silently loses to the
    vendor default.
    """
    scope = os.environ if env is None else env
    override = _role_override(scope)
    if override:
        return override
    for name in get(provider).base_url_env:
        value = str(scope.get(name, "")).strip()
        if value:
            return value
    return ""


def api_key_for(provider: str, env: dict | None = None) -> str:
    """Resolve the API key for a provider, or '' if none is set."""
    scope = os.environ if env is None else env
    for name in get(provider).key_env:
        value = str(scope.get(name, "")).strip()
        if value:
            return value
    return ""


def provider_for_model(model: str) -> str:
    """Return the registered provider a bare model id belongs to, or ''."""
    name = (model or "").strip().lower()
    for prefix, provider in MODEL_PREFIXES:
        if name.startswith(prefix):
            return provider
    return ""


def key_env_names(provider: str) -> tuple[str, ...]:
    return get(provider).key_env
