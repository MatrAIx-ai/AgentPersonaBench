from __future__ import annotations

import json
import os
import time

import usage
import re
from typing import Any, Dict, Optional, Protocol

_FENCE = re.compile(r"```(?:json)?\s*(?P<body>\{.*\})\s*```", re.DOTALL)
DEFAULT_REQUEST_TIMEOUT_SECONDS = 180.0


def coerce_json(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = _FENCE.search(text)
    if match:
        return json.loads(match.group("body"))
    start, end = text.find("{"), text.rfind("}")
    if 0 <= start < end:
        return json.loads(text[start:end + 1])
    raise ValueError("could not parse JSON from model output: {!r}".format(text[:200]))


def openai_model_supports_custom_temperature(model: str) -> bool:
    """Whether Chat Completions / Messages accepts a non-default ``temperature``.

    GPT-5 family models currently only allow the API default (1); sending
    ``0.1`` / ``0.7`` returns HTTP 400. Claude Opus 4.7+ (and Bedrock Opus)
    similarly reject an explicit non-default temperature.
    """
    lowered = (model or "").strip().lower()
    bare = lowered.rsplit("/", 1)[-1] if "/" in lowered else lowered
    if bare.startswith("gpt-5"):
        return False
    opus = re.search(r"opus-4-(\d+)", lowered)
    if opus is not None and int(opus.group(1)) >= 7:
        return False
    if "bedrock" in lowered and "opus" in lowered:
        return False
    return True


def openai_model_is_reasoning_family(model: str) -> bool:
    """Whether a model is an OpenAI reasoning model on Chat Completions.

    The reasoning families (gpt-5*, o1*, o3*, o4*) rejected the legacy
    ``max_tokens`` param with HTTP 400 ("use ``max_completion_tokens`` instead")
    and only accept the default temperature. Like the predicate above, strip a
    vendor prefix first so ``openai/o4-mini`` is recognised as the same model as
    ``o4-mini``.
    """
    lowered = (model or "").strip().lower()
    bare = lowered.rsplit("/", 1)[-1] if "/" in lowered else lowered
    return bare.startswith(("gpt-5", "o1", "o3", "o4"))


def openai_model_uses_responses(model: str) -> bool:
    """Whether a native OpenAI model should use the Responses API.

    Keep this intentionally narrow. OpenRouter, DashScope, and other
    OpenAI-compatible endpoints are not guaranteed to implement Responses; their
    builders explicitly disable this path below. GPT-5.6 reasoning and function
    tools, however, require Responses at supported reasoning efforts.
    """
    value = (model or "").strip().lower()
    if value.startswith("openai/"):
        value = value.split("/", 1)[1]
    # GPT-5.6 and up are reasoning models: tools and reasoning effort need
    # Responses, and they reject an explicit temperature on chat/completions,
    # which the arm configs do set. Listing the families rather than matching
    # `gpt-` keeps GPT-4o and friends on chat/completions where they belong.
    for family in ("gpt-5.6", "gpt-6"):
        if value == family or value.startswith(family + "-") or value.startswith(family + "."):
            return True
    return False


_GPT_5_6_REASONING_EFFORTS = frozenset(
    {"none", "low", "medium", "high", "xhigh", "max"}
)


def openai_responses_reasoning() -> Dict[str, str] | None:
    """Return the configured Responses reasoning object, if one was supplied."""
    effort = (os.environ.get("LLM_REASONING_EFFORT") or "").strip().lower()
    if not effort:
        return None
    if effort not in _GPT_5_6_REASONING_EFFORTS:
        allowed = ", ".join(sorted(_GPT_5_6_REASONING_EFFORTS))
        raise ValueError(
            "unsupported GPT-5.6 reasoning effort {!r}; expected one of {}".format(
                effort, allowed
            )
        )
    return {"effort": effort}


def _response_value(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def responses_incomplete_reason(response: Any) -> str | None:
    """Return an incomplete Responses reason, or ``None`` for complete output."""
    if _response_value(response, "status") != "incomplete":
        return None
    details = _response_value(response, "incomplete_details")
    return str(_response_value(details, "reason", "unknown") or "unknown")


def responses_output_text(response: Any) -> str:
    """Extract text from an SDK or dict-shaped Responses API result."""
    direct = _response_value(response, "output_text")
    if direct:
        return str(direct)
    parts = []
    for item in _response_value(response, "output", []) or []:
        if _response_value(item, "type") != "message":
            continue
        for block in _response_value(item, "content", []) or []:
            if _response_value(block, "type") in {"output_text", "text"}:
                text = _response_value(block, "text", "")
                if text:
                    parts.append(str(text))
    return "".join(parts)


class ChatClient(Protocol):
    def complete_json(self, system: str, user: str) -> Dict[str, Any]: ...


class OpenAIChatClient:
    """OpenAI v1 client (`from openai import OpenAI`) using JSON response mode."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        client: Optional[Any] = None,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS,
        use_responses_api: bool | None = None,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self.use_responses_api = (
            openai_model_uses_responses(model)
            if use_responses_api is None
            else use_responses_api
        )
        if client is None:
            from openai import OpenAI  # lazy: tests inject a fake

            client_kwargs: Dict[str, Any] = {}
            if api_key is not None:
                client_kwargs["api_key"] = api_key
            if base_url is not None:
                client_kwargs["base_url"] = base_url
            # Parallel suites saturate the per-model tokens-per-minute limit; the
            # SDK's default two retries give up while it is still full. It honours
            # the Retry-After of a 429, so more attempts ride the limit out.
            client_kwargs.setdefault("max_retries", 8)
            client = OpenAI(**client_kwargs)
        self._client = client

    def complete_json(self, system: str, user: str) -> Dict[str, Any]:
        if self.use_responses_api:
            kwargs: Dict[str, Any] = {
                "model": self.model,
                # JSON mode requires the input itself (not only `instructions`)
                # to mention JSON. Keep that API precondition local to this
                # JSON-only client so callers do not each have to remember it.
                "input": user + "\n\nReturn only a valid JSON object.",
                "text": {"format": {"type": "json_object"}},
                "store": False,
                "timeout": self.timeout_seconds,
            }
            if system:
                kwargs["instructions"] = system
            reasoning = openai_responses_reasoning()
            if reasoning is not None:
                kwargs["reasoning"] = reasoning
            _started = time.time()
            response = self._client.responses.create(**kwargs)
            usage.record_response(self.model, response, _started, "persona-sim")
            incomplete_reason = responses_incomplete_reason(response)
            if incomplete_reason is not None:
                raise RuntimeError(
                    "OpenAI Responses JSON output was incomplete: {}".format(
                        incomplete_reason
                    )
                )
            return coerce_json(responses_output_text(response))

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "timeout": self.timeout_seconds,
        }
        if openai_model_supports_custom_temperature(self.model):
            kwargs["temperature"] = self.temperature
        _started = time.time()
        completion = self._client.chat.completions.create(**kwargs)
        usage.record_response(self.model, completion, _started, "persona-sim")
        return coerce_json(completion.choices[0].message.content)
