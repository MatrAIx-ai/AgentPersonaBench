"""Cost of a run, in USD — one place that knows how tokens become dollars.

Every arm must report what it cost or the comparison is incomplete: a model that
wins by a point while costing twenty times more has not really won. Pricing comes
from LiteLLM's table, which covers the providers this benchmark routes to
(anthropic, openai, gemini, zai, dashscope, openrouter).

Two rules this module keeps:

* **Never invent a price.** A model LiteLLM has no entry for returns ``None``,
  not zero. A silent $0.00 next to a real cost is worse than an honest blank,
  because it reads as "this arm was free".
* **Price against the provider-qualified id.** LiteLLM prices ``zai/glm-5.3-flash``
  but not the bare ``glm-5.3-flash``, and the arm config carries the bare form,
  so the provider has to be reattached before the lookup.

Cached input is billed separately, and not as a rounding difference: GLM-5.3-Flash
reads a cached token at a fifth of a fresh one, and 42% of the prompt tokens in a
recorded Qwen run were cache hits. Pricing every prompt token at the fresh rate
would overstate a run badly, so cached tokens are split out and charged at the
provider's cache-read rate.

An arm whose model LiteLLM does not know can still be priced by declaring rates
in its config, in dollars per million tokens::

    "price_per_mtok": {"input": 0.15, "cached_input": 0.03, "output": 0.50}

``cached_input`` is optional; without it cached tokens are charged as fresh input.
"""
from __future__ import annotations

from typing import Any

_MILLION = 1_000_000


def _from_litellm(model: str) -> tuple[float, float, float] | None:
    """(input, cached input, output) dollars per token, or None if unknown."""
    try:
        import litellm
    except Exception:  # noqa: BLE001 - absent, or a broken/partial install
        # Pricing is telemetry; a provider table that will not import must never
        # take a benchmark run down with it.
        return None
    # Looking up a model LiteLLM does not know is the normal case here, not an
    # error, and its banner on every miss buries the actual output.
    litellm.suppress_debug_info = True
    try:
        info = litellm.get_model_info(model)
    except Exception:  # noqa: BLE001 - an unknown model raises; that is a "no price"
        return None
    per_in = float(info.get("input_cost_per_token") or 0.0)
    per_out = float(info.get("output_cost_per_token") or 0.0)
    if not per_in and not per_out:
        return None
    # No cache-read rate published means cached tokens bill as fresh ones.
    per_cached = float(info.get("cache_read_input_token_cost") or 0.0) or per_in
    return per_in, per_cached, per_out


def rates_for(model: str, provider: str = "", arm_config: dict[str, Any] | None = None
              ) -> tuple[float, float, float] | None:
    """(input, cached input, output) dollars per token, or None when unpriced."""
    override = ((arm_config or {}).get("price_per_mtok") or {})
    if override:
        try:
            per_in = float(override.get("input", 0)) / _MILLION
            cached = override.get("cached_input")
            return (per_in,
                    float(cached) / _MILLION if cached is not None else per_in,
                    float(override.get("output", 0)) / _MILLION)
        except (TypeError, ValueError):
            pass
    bare = (model or "").strip()
    if not bare:
        return None
    candidates = []
    if provider and "/" not in bare:
        candidates.append(f"{provider}/{bare}")
    candidates.append(bare)
    if "/" in bare:
        candidates.append(bare.split("/", 1)[1])
    for candidate in candidates:
        rates = _from_litellm(candidate)
        if rates:
            return rates
    return None


def cost_usd(model: str, prompt_tokens: int, completion_tokens: int,
             provider: str = "", arm_config: dict[str, Any] | None = None,
             cached_tokens: int = 0) -> float | None:
    """Cost of one call or one aggregate, or None when the model has no price.

    ``cached_tokens`` is the cache-hit subset of ``prompt_tokens`` (that is how
    every provider here reports it), charged at the cache-read rate; the rest is
    charged as fresh input.
    """
    rates = rates_for(model, provider, arm_config)
    if rates is None:
        return None
    per_in, per_cached, per_out = rates
    cached = max(0, min(int(cached_tokens or 0), int(prompt_tokens or 0)))
    fresh = (prompt_tokens or 0) - cached
    return round(fresh * per_in + cached * per_cached
                 + (completion_tokens or 0) * per_out, 6)
