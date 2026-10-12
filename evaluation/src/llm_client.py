"""Provider-agnostic LLM client — the evaluation framework's single call layer.

Every task's solver and every LLM-judge verifier calls `chat(messages, model)`.
The concrete backend is chosen by the arm config's `provider` (exported by
run_task.py as LLM_PROVIDER), so a task never hardcodes a vendor:

    provider="anthropic"  -> Anthropic native SDK      (claude-*)
    provider="openai"     -> OpenAI native SDK          (gpt-*)
    provider="gemini"     -> Google GenAI native SDK    (gemini-*)

`messages` uses the OpenAI chat shape ([{"role","content"}, ...]) as the common
interface; each backend adapts it to its own SDK. `chat()` returns the assistant
text. A per-process call log records tokens/latency for the trial envelope, so
accounting is identical across providers.

Keys come from the standard per-provider env vars (ANTHROPIC_API_KEY /
OPENAI_API_KEY / GEMINI_API_KEY|GOOGLE_API_KEY), loaded lazily so importing this
module never requires a key.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
import time

import openai_compat
import usage as _usage
from playground.openai_client import (
    openai_model_is_reasoning_family,
    openai_model_uses_responses,
    openai_responses_reasoning,
    responses_incomplete_reason,
    responses_output_text,
)
from playground import reasoning as _reasoning

# --- provider selection ------------------------------------------------------
# The arm under test sets LLM_PROVIDER (from configs/<arm>.json via run_task.py).
# A bare model name is also enough to infer the provider, so ad-hoc calls without
# the env still route correctly.
DEFAULT_MODEL = os.environ.get("LLM_MODEL", "claude-opus-4-8")
logger = logging.getLogger(__name__)

# Reasoning models bill hidden reasoning tokens against the same output budget
# as the answer. The chat verifiers ask the judge for a one-word label with
# max_tokens=16, which gpt-5.6-luna spends entirely on reasoning: it returns an
# empty string, the verifier fails strict parsing three times, and the trial is
# recorded as a model failure. Floor the budget for these families so a small
# answer still leaves room to think. Only generated tokens are billed, so the
# floor does not change the cost of a verdict.
REASONING_MIN_BUDGET = int(os.environ.get("LLM_REASONING_MIN_BUDGET", "4096"))


_ROLE_LOCK = __import__("threading").RLock()


def _inferred_provider(model: str) -> str:
    m = model.lower()
    if m.startswith("gpt-") or m.startswith("o1") or m.startswith("o3"):
        return "openai"
    if m.startswith("gemini"):
        return "gemini"
    # qwen-* / glm-* reach an OpenAI-compatible endpoint that is not OpenAI's, so
    # the name alone has to pick the right base URL (see openai_compat).
    compatible = openai_compat.provider_for_model(m)
    if compatible:
        return compatible
    return "anthropic"  # claude-* and anything else


def _provider_for(model: str) -> str:
    explicit = os.environ.get("LLM_PROVIDER", "").strip().lower()
    call_role = os.environ.get("LLM_CALL_ROLE", "").strip().lower()

    # The arm provider and benchmark judge provider are independent. The runner
    # marks solve calls as "arm" and verifier calls as "judge" so the two remain
    # distinguishable even when they use the same model id. Keep the model-name
    # fallback for standalone verifiers that do not set LLM_CALL_ROLE.
    judge_model = os.environ.get("ADHERENCE_JUDGE_MODEL", "").strip()
    if (
        call_role != "arm"
        and judge_model
        and model.strip().lower() == judge_model.lower()
    ):
        judge_provider = os.environ.get("ADHERENCE_JUDGE_PROVIDER", "").strip().lower()
        return judge_provider or _inferred_provider(model)

    if call_role == "bot":
        # the fixed chat bot: its own provider, never the arm's
        return os.environ.get("APB_CHAT_BOT_PROVIDER", "").strip().lower() or _inferred_provider(model)
    return explicit or _inferred_provider(model)


# --- lightweight call log (per-process) --------------------------------------
# Solvers record token usage / latency of every generation for the trial
# envelope. Kept here so every task shares one accounting format regardless of
# which provider served the call.
# The shared log (evaluation/src/usage.py), so a chat trial's bot turns — which
# come through here — are counted alongside the persona simulator's turns, which
# come through the playground clients. One list, one total.
_CALL_LOG: list[dict] = _usage.CALL_LOG


def reset_call_log() -> None:
    """Clear the per-process call log (call at the start of a solve)."""
    _CALL_LOG.clear()


def get_call_log() -> list[dict]:
    """Return the raw per-call records (model, tokens, latency)."""
    return list(_CALL_LOG)


def call_log_summary() -> dict:
    """Aggregate the call log: #calls, total tokens, total latency (s).

    Deliberately no cost: cost is derived at report time from these token counts
    (see evaluation/src/pricing.py and report_suite.resolved_cost). Keeping it out
    of here leaves this contract as upstream defines it, and means a change to a
    provider's prices re-prices past runs instead of freezing a stale number into
    every envelope.
    """
    return {
        "calls": len(_CALL_LOG),
        "total_tokens": sum(c.get("total_tokens", 0) for c in _CALL_LOG),
        "prompt_tokens": sum(c.get("prompt_tokens", 0) for c in _CALL_LOG),
        "completion_tokens": sum(c.get("completion_tokens", 0) for c in _CALL_LOG),
        "latency_s": round(sum(c.get("latency_s", 0.0) for c in _CALL_LOG), 3),
    }


def _record(model: str, prompt_tokens: int, completion_tokens: int,
            total_tokens: int, t0: float) -> None:
    _CALL_LOG.append({
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens or (prompt_tokens + completion_tokens),
        "latency_s": round(time.time() - t0, 3),
    })


# --- token loading (per provider) --------------------------------------------
_KEY_ENV = {
    "anthropic": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
    "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    # openai, dashscope (Qwen), zai (GLM), openrouter — one entry each, from the
    # registry, so a new OpenAI-compatible provider is added in exactly one place.
    **{name: list(spec.key_env) for name, spec in openai_compat.REGISTRY.items()},
}


def load_token(provider: str | None = None) -> str:
    """Return the API key for a provider from its standard env var(s)."""
    provider = (provider or _provider_for(DEFAULT_MODEL)).lower()
    for env in _KEY_ENV.get(provider, []):
        val = os.environ.get(env)
        if val:
            return val.strip()
    envs = " or ".join(_KEY_ENV.get(provider, ["<unknown provider>"]))
    raise RuntimeError(f"No {provider} API key: set {envs}")


# --- OpenAI-shape messages -> provider-native adapters ------------------------
def _split_system(messages: list[dict]) -> tuple[str, list[dict]]:
    """Pull any leading system messages into one string; return (system, rest).

    Anthropic and Gemini take the system prompt out-of-band, not as a message.
    """
    system_parts, rest = [], []
    for m in messages:
        if m.get("role") == "system":
            system_parts.append(str(m.get("content", "")))
        else:
            rest.append(m)
    return "\n\n".join(system_parts).strip(), rest


# A message's content is either a string or a list of parts in the OpenAI chat
# shape: {"type": "text", "text": ...} and {"type": "image_url", "image_url":
# {"url": "data:image/png;base64,..."}} (the web agent's screenshots). Chat
# Completions takes that list as-is; the other APIs get it translated here.
def _parts(content) -> list[dict]:
    if isinstance(content, list):
        return content
    return [{"type": "text", "text": str(content)}]


def _data_url(part: dict) -> tuple[str, str]:
    """(media_type, base64 data) of an image_url part holding a data: URL."""
    url = part["image_url"]["url"] if isinstance(part.get("image_url"), dict) else part["image_url"]
    head, _, data = url.partition(",")
    if not head.startswith("data:") or not head.endswith(";base64"):
        raise ValueError("image parts must be base64 data: URLs")
    return head[len("data:"):-len(";base64")], data


def _anthropic_content(content):
    if isinstance(content, str):
        return content
    out = []
    for p in content:
        if p.get("type") == "image_url":
            media, data = _data_url(p)
            out.append({"type": "image", "source": {"type": "base64", "media_type": media, "data": data}})
        else:
            out.append({"type": "text", "text": p["text"]})
    return out


def _responses_input(convo: list[dict]):
    """Chat messages as Responses API input items (images become input_image)."""
    items = []
    for m in convo:
        if isinstance(m["content"], str):
            items.append(m)
            continue
        text_type = "output_text" if m["role"] == "assistant" else "input_text"
        items.append({"role": m["role"], "content": [
            {"type": "input_image", "image_url": (p["image_url"]["url"] if isinstance(p["image_url"], dict)
                                                  else p["image_url"])}
            if p.get("type") == "image_url" else {"type": text_type, "text": p["text"]}
            for p in m["content"]]})
    return items


def _gemini_parts(content) -> list[dict]:
    out = []
    for p in _parts(content):
        if p.get("type") == "image_url":
            media, data = _data_url(p)
            out.append({"inline_data": {"mime_type": media, "data": base64.b64decode(data)}})
        else:
            out.append({"text": p["text"]})
    return out


# --- provider backends -------------------------------------------------------
def _chat_anthropic(messages, model, max_tokens, temperature, token, timeout) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=token, timeout=timeout)
    system, convo = _split_system(messages)
    # Opus 4.8 / 4.7 reject temperature/top_p/top_k — never send them for claude-*.
    # The suite's --effort becomes Claude's thinking config; without it Opus 4.8
    # and Haiku 4.5 do not think at all while Opus 5 thinks at its default (high).
    thinking, max_tokens = _reasoning.claude_thinking(model, _reasoning.env_effort(), max_tokens)
    kwargs = dict(model=model, max_tokens=max_tokens,
                  messages=[{"role": m["role"], "content": _anthropic_content(m["content"])}
                            for m in convo],
                  **thinking)
    if system:
        kwargs["system"] = system
    t0 = time.time()
    resp = client.messages.create(**kwargs)
    u = resp.usage
    _record(model, getattr(u, "input_tokens", 0), getattr(u, "output_tokens", 0),
            getattr(u, "input_tokens", 0) + getattr(u, "output_tokens", 0), t0)
    return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")


def _chat_openai(messages, model, max_tokens, temperature, token, timeout,
                 base_url: str = "", use_responses_api: bool = True) -> str:
    import openai

    kwargs = {"api_key": token, "timeout": timeout}
    if base_url:
        kwargs["base_url"] = base_url
    client = openai.OpenAI(**kwargs)
    t0 = time.time()
    if openai_model_is_reasoning_family(model):
        max_tokens = max(max_tokens, REASONING_MIN_BUDGET)
    if use_responses_api and openai_model_uses_responses(model):
        system, conversation = _split_system(messages)
        kwargs = {
            "model": model,
            "input": _responses_input(conversation) or "",
            "max_output_tokens": max_tokens,
            "store": False,
        }
        if system:
            kwargs["instructions"] = system
        reasoning = openai_responses_reasoning()
        if reasoning is not None:
            kwargs["reasoning"] = reasoning
        resp = client.responses.create(**kwargs)
        incomplete_reason = responses_incomplete_reason(resp)
        if incomplete_reason not in (None, "max_output_tokens"):
            raise RuntimeError(
                "OpenAI Responses text output was incomplete: {}".format(
                    incomplete_reason
                )
            )
        u = resp.usage
        _record(
            model,
            getattr(u, "input_tokens", 0),
            getattr(u, "output_tokens", 0),
            getattr(u, "total_tokens", 0),
            t0,
        )
        text = responses_output_text(resp)
        if incomplete_reason == "max_output_tokens":
            logger.warning(
                "OpenAI Responses text output was incomplete: %s; "
                "returning available text",
                incomplete_reason,
            )
            return text
        if not text:
            raise RuntimeError("OpenAI Responses returned no text for model {}".format(model))
        return text

    # The reasoning families reject the legacy `max_tokens` (HTTP 400: use
    # `max_completion_tokens`) and any non-default temperature, so send the
    # budget under the name they accept and leave temperature to the API
    # default. Everything else keeps the classic pair.
    if openai_model_is_reasoning_family(model):
        budget = {"max_completion_tokens": max_tokens}
    else:
        budget = {"max_tokens": max_tokens, "temperature": temperature}
    resp = client.chat.completions.create(
        model=model, messages=messages, **budget,
    )
    u = resp.usage
    _record(model, getattr(u, "prompt_tokens", 0), getattr(u, "completion_tokens", 0),
            getattr(u, "total_tokens", 0), t0)
    return resp.choices[0].message.content or ""


def gemini_vertex() -> dict | None:
    """Vertex AI settings when Gemini is billed to a GCP project instead of an
    AI Studio key: GOOGLE_GENAI_USE_VERTEXAI=true plus application-default
    credentials (`gcloud auth application-default login`). No key is used."""
    if (os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") or "").strip().lower() not in ("1", "true", "yes"):
        return None
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or ""
    if not project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is required when GOOGLE_GENAI_USE_VERTEXAI=true")
    return {"project": project,
            "location": os.environ.get("GOOGLE_CLOUD_LOCATION") or "global"}


def _chat_gemini(messages, model, max_tokens, temperature, token, timeout) -> str:
    from google import genai
    from google.genai import types

    vertex = gemini_vertex()
    client = genai.Client(vertexai=True, **vertex) if vertex else genai.Client(api_key=token)
    system, convo = _split_system(messages)
    # Gemini contents: user/model roles; assistant -> "model".
    contents = [
        {"role": ("model" if m["role"] == "assistant" else "user"),
         "parts": _gemini_parts(m["content"])}
        for m in convo
    ]
    cfg_kwargs = dict(max_output_tokens=max_tokens, temperature=temperature,
                      system_instruction=(system or None))
    # Gemini 3 thinks at its default level (high) unless told otherwise.
    level = _reasoning.gemini_thinking_level(model, _reasoning.env_effort())
    if level:
        cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=level)
        # Thinking shares max_output_tokens, as reasoning does on OpenAI: a
        # caller's short budget (a one-word judge, a 200-token web pick) would
        # otherwise be spent before the answer starts.
        cfg_kwargs["max_output_tokens"] = max(max_tokens, REASONING_MIN_BUDGET)
    cfg = types.GenerateContentConfig(**cfg_kwargs)
    t0 = time.time()
    resp = client.models.generate_content(model=model, contents=contents, config=cfg)
    um = getattr(resp, "usage_metadata", None)
    _record(model,
            getattr(um, "prompt_token_count", 0) or 0,
            getattr(um, "candidates_token_count", 0) or 0,
            getattr(um, "total_token_count", 0) or 0, t0)
    return resp.text or ""


def _openai_compatible_backend(provider: str):
    """Bind the OpenAI adapter to one provider's endpoint.

    Resolving the base URL per call (not at import) keeps the client honest when a
    verifier changes LLM_CALL_ROLE between the solve and judge phases of a trial.
    """
    def _backend(messages, model, max_tokens, temperature, token, timeout):
        return _chat_openai(
            messages, model, max_tokens, temperature, token, timeout,
            base_url=openai_compat.base_url_for(provider),
            use_responses_api=openai_compat.get(provider).supports_responses_api,
        )

    _backend.__name__ = f"_chat_{provider}"
    return _backend


_BACKENDS = {
    "anthropic": _chat_anthropic,
    "gemini": _chat_gemini,
    **{name: _openai_compatible_backend(name) for name in openai_compat.REGISTRY},
}


def chat(
    messages,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 1024,
    temperature: float = 0.0,
    token: str | None = None,
    retries: int = 8,
    timeout: int = 90,
    *,
    call_role: str | None = None,
) -> str:
    """One chat completion; returns the assistant text. Retries transient errors.

    Backend is chosen by LLM_PROVIDER (or inferred from the model name). `messages`
    is the OpenAI chat shape; each backend adapts it. `temperature` is ignored for
    Anthropic models, which reject sampling params."""
    if call_role:
        # A benchmark-side call made from inside an arm's solve (the chat bot):
        # resolve provider, key and endpoint for that role, not the arm's
        # LLM_PROVIDER. Serialised: the role is read from the environment.
        with _ROLE_LOCK:
            saved = os.environ.get("LLM_CALL_ROLE")
            os.environ["LLM_CALL_ROLE"] = call_role
            try:
                return chat(messages, model, max_tokens, temperature, token, retries, timeout)
            finally:
                if saved is None:
                    os.environ.pop("LLM_CALL_ROLE", None)
                else:
                    os.environ["LLM_CALL_ROLE"] = saved
    provider = _provider_for(model)
    backend = _BACKENDS.get(provider)
    if backend is None:
        raise RuntimeError(f"unknown provider '{provider}' (model={model})")
    if not (provider == "gemini" and gemini_vertex()):
        token = token or load_token(provider)

    last_err = None
    for attempt in range(retries):
        try:
            return backend(messages, model, max_tokens, temperature, token, timeout)
        except Exception as e:  # noqa: BLE001 — retry transient, re-raise terminal below
            last_err = e
            # Retry only on transient signals (rate limit / overload / timeout /
            # connection); give up fast on 4xx request errors.
            msg = str(e).lower()
            transient = any(s in msg for s in (
                "rate limit", "429", "overload", "529", "timeout", "timed out",
                "temporarily", "connection", "503", "502", "500", "504",
            ))
            if not transient or attempt == retries - 1:
                raise
            # A 429 says how long to wait ("Please try again in 1.2s"); honour it,
            # else back off exponentially, capped at a minute.
            m = re.search(r"try again in ([\d.]+)\s*(ms|s)", msg)
            wait = (float(m.group(1)) / (1000 if m.group(2) == "ms" else 1) + 0.5) if m else min(60, 2 ** attempt)
            time.sleep(wait)
    raise RuntimeError(f"chat failed after {retries} retries: {last_err}")


def extract_json(text: str):
    """Pull the first JSON object out of a model response (handles ```json fences)."""
    t = text.strip()
    if "```" in t:
        for p in t.split("```"):
            p = p.strip()
            if p.startswith("json"):
                p = p[4:].strip()
            if p.startswith("{"):
                t = p
                break
    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object in response: {text[:200]}")
    return json.loads(t[start:end + 1])
