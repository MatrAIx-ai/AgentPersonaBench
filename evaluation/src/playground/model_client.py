from __future__ import annotations

import json
import os
import time

import usage
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

# Large survey envelopes (e.g. CFPB ~134 answers) need far more than a short chat reply.
# 1200 truncates mid-JSON; keep headroom once the system prompt already carries the
# full 1290-dim persona profile + questionnaire.
from matraix.persona_agent_context import SURVEY_MAX_OUTPUT_TOKENS as ANTHROPIC_JSON_MAX_TOKENS
from playground.openai_client import (
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    OpenAIChatClient,
    coerce_json,
    openai_model_supports_custom_temperature,
)

DASHSCOPE_DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
OPENROUTER_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


def dashscope_model_id(model: str) -> str:
    """Return the bare DashScope model id from a Harbor persona model string."""
    value = (model or "").strip()
    if value.startswith("dashscope/"):
        return value.split("/", 1)[1]
    return value


def gemini_openai_client_kwargs(model: str) -> Dict[str, str]:
    """OpenAI-compatible client settings for a Gemini model (the chat persona and
    self-report clients speak the OpenAI API).

    With GOOGLE_GENAI_USE_VERTEXAI=true it is Vertex AI on the GCP project
    (application-default credentials; the access token is the API key, valid for
    an hour, longer than any chat trial), otherwise AI Studio with GEMINI_API_KEY.
    """
    bare = model.split("/", 1)[1] if model.startswith(("gemini/", "google/", "vertex_ai/")) else model
    if (os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") or "").strip().lower() in ("1", "true", "yes"):
        from google.auth import default as google_default_credentials
        from google.auth.transport.requests import Request

        creds, _ = google_default_credentials(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        creds.refresh(Request())
        project = os.environ.get("GOOGLE_CLOUD_PROJECT") or ""
        if not project:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT is required when GOOGLE_GENAI_USE_VERTEXAI=true")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION") or "global"
        host = "aiplatform.googleapis.com" if location == "global" else f"{location}-aiplatform.googleapis.com"
        return {"model": f"google/{bare}", "api_key": creds.token,
                "base_url": f"https://{host}/v1/projects/{project}/locations/{location}/endpoints/openapi"}
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
    if not key:
        raise RuntimeError("GEMINI_API_KEY (or GOOGLE_GENAI_USE_VERTEXAI=true) is required for {!r}".format(model))
    return {"model": bare, "api_key": key,
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/"}


def dashscope_openai_client_kwargs(model: str) -> Dict[str, str]:
    """OpenAI SDK kwargs for Alibaba DashScope compatible-mode chat."""
    api_key = (os.environ.get("DASHSCOPE_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError(
            "DASHSCOPE_API_KEY is required for persona model {!r}".format(model)
        )
    base_url = (
        os.environ.get("DASHSCOPE_API_BASE")
        or os.environ.get("LLM_BASE_URL")
        or DASHSCOPE_DEFAULT_BASE_URL
    ).strip()
    return {
        "model": dashscope_model_id(model),
        "api_key": api_key,
        "base_url": base_url,
    }


def openrouter_model_id(model: str) -> str:
    """Return the bare OpenRouter model id from a Harbor persona model string."""
    value = (model or "").strip()
    if value.startswith("openrouter/"):
        return value.split("/", 1)[1]
    return value


def openrouter_openai_client_kwargs(model: str) -> Dict[str, str]:
    """OpenAI SDK kwargs for OpenRouter chat."""
    api_key = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is required for persona model {!r}".format(model)
        )
    base_url = (
        os.environ.get("OPENROUTER_API_BASE")
        or os.environ.get("OPENROUTER_BASE_URL")
        or OPENROUTER_DEFAULT_BASE_URL
    ).strip()
    return {
        "model": openrouter_model_id(model),
        "api_key": api_key,
        "base_url": base_url,
    }


class AnthropicJSONClient:
    """Minimal Anthropic Messages client that returns a JSON object."""

    def __init__(
        self,
        model: str,
        *,
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS,
        max_tokens: int = ANTHROPIC_JSON_MAX_TOKENS,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens
        self.api_key = (
            api_key
            or os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("CLAUDE_API_KEY")
            or ""
        ).strip()
        self.base_url = "https://api.anthropic.com/v1/messages"
        if not self.api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY or CLAUDE_API_KEY is required for persona model {}".format(
                    model
                )
            )

    def complete_json(self, system: str, user: str) -> Dict[str, Any]:
        body = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system,
            "messages": [
                {
                    "role": "user",
                    "content": user
                    + "\n\nReturn only a valid JSON object. Do not include markdown.",
                }
            ],
        }
        if openai_model_supports_custom_temperature(self.model):
            body["temperature"] = self.temperature
        _headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        request = urllib.request.Request(
            self.base_url,
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers=_headers,
        )
        _started = time.time()
        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
            usage.record_response(self.model, payload, _started, "persona-sim")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                "Anthropic persona model request failed: HTTP {} {}".format(
                    exc.code, detail[:500]
                )
            ) from exc
        except (TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                "Anthropic persona model request failed: {}".format(exc)
            ) from exc

        text_parts = []
        for block in payload.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(str(block.get("text") or ""))
        text = "\n".join(text_parts)
        if payload.get("stop_reason") == "max_tokens":
            raise RuntimeError(
                "Anthropic persona model output truncated at max_tokens={} "
                "(incomplete JSON). Increase max_tokens for large survey envelopes.".format(
                    self.max_tokens
                )
            )
        return coerce_json(text)


def _llm_proxy_base_url() -> str:
    """Return the LiteLLM proxy base URL if proxy mode is on, else ''.

    When set, OpenAI-family clients already route through the proxy via the
    openai SDK's OPENAI_BASE_URL handling, so we can send Claude through the
    proxy's OpenAI-compatible endpoint too and share the global rate limiter
    (instead of the direct-to-Anthropic urllib client).
    """
    return (
        os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_API_BASE") or ""
    ).strip()


def _llm_request_timeout_seconds() -> float:
    """Return the configured OpenAI-compatible request timeout."""
    value = os.environ.get("LLM_REQUEST_TIMEOUT_SECONDS")
    if value is None:
        return DEFAULT_REQUEST_TIMEOUT_SECONDS
    try:
        return float(value)
    except ValueError:
        return DEFAULT_REQUEST_TIMEOUT_SECONDS


def _registered_compatible_client(value: str, temperature: float,
                                  timeout_seconds: float) -> Any | None:
    """Client for an OpenAI-compatible provider named by LLM_PROVIDER or by the
    model id itself (``qwen-*`` -> DashScope, ``glm-*`` -> Z.ai), else None.

    Without this, a bare id such as ``glm-5.3`` fell through to the Anthropic
    branch below and was posted to api.anthropic.com, which is the one place the
    chat surface diverged from every other surface: the arm config already said
    which provider to use, and only this function ignored it.
    """
    import openai_compat

    provider = (os.environ.get("LLM_PROVIDER") or "").strip().lower()
    if not openai_compat.is_openai_compatible(provider):
        provider = openai_compat.provider_for_model(value)
    if not provider:
        return None
    api_key = openai_compat.api_key_for(provider)
    if not api_key:
        raise RuntimeError(
            "{} is required for persona model {!r}".format(
                " or ".join(openai_compat.key_env_names(provider)), value
            )
        )
    client_kwargs = {
        "model": value,
        "api_key": api_key,
        "temperature": temperature,
        "timeout_seconds": timeout_seconds,
    }
    base_url = openai_compat.base_url_for(provider)
    if base_url:
        client_kwargs["base_url"] = base_url
    return OpenAIChatClient(**client_kwargs)


def build_json_client(model: str, *, temperature: float = 0.7) -> Any:
    """Return a JSON-mode client for a configured persona model string."""
    value = (model or "openai/gpt-4o-mini").strip()
    timeout_seconds = _llm_request_timeout_seconds()
    if value.startswith("anthropic/"):
        if _llm_proxy_base_url():
            # Route Claude through the proxy's OpenAI-compatible endpoint; base
            # url + api key come from OPENAI_* env (proxy master key).
            return OpenAIChatClient(
                model=value,
                temperature=temperature,
                timeout_seconds=timeout_seconds,
                use_responses_api=False,
            )
        return AnthropicJSONClient(value.split("/", 1)[1], temperature=temperature)
    if value.startswith("dashscope/"):
        kwargs = dashscope_openai_client_kwargs(value)
        return OpenAIChatClient(
            model=kwargs["model"],
            api_key=kwargs["api_key"],
            base_url=kwargs["base_url"],
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            use_responses_api=False,
        )
    if value.startswith("zai/") or value.startswith("glm/"):
        bare = value.split("/", 1)[1]
        client = _registered_compatible_client(bare, temperature, timeout_seconds)
        if client is not None:
            return client
    if value.startswith(("gemini", "google/")):
        kwargs = gemini_openai_client_kwargs(value)
        return OpenAIChatClient(
            model=kwargs["model"],
            api_key=kwargs["api_key"],
            base_url=kwargs["base_url"],
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            use_responses_api=False,
        )
    if value.startswith("openrouter/"):
        kwargs = openrouter_openai_client_kwargs(value)
        return OpenAIChatClient(
            model=kwargs["model"],
            api_key=kwargs["api_key"],
            base_url=kwargs["base_url"],
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            use_responses_api=False,
        )
    if value.startswith("openai/"):
        return OpenAIChatClient(
            model=value.split("/", 1)[1],
            temperature=temperature,
            timeout_seconds=timeout_seconds,
        )
    if value.startswith("gpt-"):
        return OpenAIChatClient(
            model=value,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
        )
    compatible = _registered_compatible_client(value, temperature, timeout_seconds)
    if compatible is not None:
        return compatible
    return AnthropicJSONClient(value, temperature=temperature)
