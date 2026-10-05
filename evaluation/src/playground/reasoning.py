"""The suite's --effort, translated into each vendor's own request fields.

Every arm records `effort` (medium by default) in its envelope, but until this
module only the OpenAI text path turned it into a request field. Claude text
calls sent no thinking config, so Opus 4.8 and Haiku 4.5 answered without
thinking while Opus 5 thought at its own default (high); Gemini's native
backends left thinking at the model default (high); and the native
computer-use providers ignored effort altogether. The same "medium" therefore
meant a different amount of reasoning per vendor and per surface.

Callers pass the effort string they were given (run_task exports
LLM_REASONING_EFFORT; harbor agents receive reasoning_effort). An empty or
unknown effort changes nothing, so an arm that never set one keeps the model
default exactly as before. Stdlib only: imported by llm_client on the host and
lazily by the harbor computer-use providers.
"""
from __future__ import annotations

import os

# Claude models that take adaptive thinking + output_config.effort. Anything
# else (Haiku 4.5, Sonnet 4.5 and older) takes a fixed budget_tokens and
# rejects `effort`.
_CLAUDE_ADAPTIVE = ("opus-4-6", "opus-4-7", "opus-4-8", "opus-5", "sonnet-4-6",
                    "sonnet-5", "fable-5", "mythos-5")
_CLAUDE_EFFORTS = {"low", "medium", "high", "xhigh", "max"}
# Fixed budgets for the budget_tokens models: LiteLLM's own reasoning_effort
# table, so a call made here and one made through a LiteLLM-backed harness
# (openhands-sdk, computer-1's generic path) think with the same budget.
_CLAUDE_BUDGET = {"low": 1024, "medium": 2048, "high": 4096, "xhigh": 8192, "max": 8192}
# Thinking shares max_tokens with the answer; an arm configured for short
# answers (opus-4-8 ships max_tokens=1200) would otherwise come back empty.
CLAUDE_THINKING_MIN_MAX_TOKENS = 16000

_GEMINI_LEVELS = {"minimal", "low", "medium", "high"}


def env_effort() -> str:
    return (os.environ.get("LLM_REASONING_EFFORT") or "").strip().lower()


def _norm_claude(effort: str) -> str | None:
    effort = (effort or "").strip().lower()
    if effort in ("minimal", "none"):
        return "low"
    return effort if effort in _CLAUDE_EFFORTS else None


def claude_thinking(model: str, effort: str | None, max_tokens: int) -> tuple[dict, int]:
    """Request fields that enable thinking at *effort*, and the max_tokens to use.

    Returns ({}, max_tokens) when effort is unset or unknown.
    """
    level = _norm_claude(effort or "")
    if level is None:
        return {}, max_tokens
    name = (model or "").lower()
    if any(tag in name for tag in _CLAUDE_ADAPTIVE):
        return ({"thinking": {"type": "adaptive"}, "output_config": {"effort": level}},
                max(max_tokens, CLAUDE_THINKING_MIN_MAX_TOKENS))
    budget = _CLAUDE_BUDGET[level]
    # budget_tokens must be >= 1024 and < max_tokens; keep the arm's own answer
    # budget on top of the thinking budget.
    return ({"thinking": {"type": "enabled", "budget_tokens": budget}},
            budget + max(max_tokens, 1024))


def gemini_thinking_level(model: str, effort: str | None) -> str | None:
    """thinking_level for a Gemini 3 model at *effort*, else None."""
    if not (model or "").lower().removeprefix("gemini/").startswith("gemini-3"):
        return None
    effort = (effort or "").strip().lower()
    if effort in ("xhigh", "max"):
        return "high"
    if effort == "none":
        return "minimal"
    return effort if effort in _GEMINI_LEVELS else None


def openai_reasoning(effort: str | None) -> dict | None:
    """Responses-API `reasoning` object at *effort*, else None."""
    effort = (effort or "").strip().lower()
    # Same set the OpenAI text path accepts (openai_client._GPT_5_6_REASONING_EFFORTS).
    if effort in ("none", "low", "medium", "high", "xhigh", "max"):
        return {"effort": effort}
    return None
