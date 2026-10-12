"""Per-process record of every model call — the one place token spend is counted.

Cost is derived from tokens at report time, so a surface whose tokens are never
recorded is a surface whose spend is invisible. That was the state of the chat
surface: its persona clients discarded the `usage` block every provider returns,
so 0 of 32 chat trials reported a single token while being the most expensive
surface in the set.

`llm_client` (the provider layer behind survey/web solvers and the LLM judge) and
the playground clients that drive a chat persona both append here, so a trial's
total is the sum of everything it actually spent, whichever path made the call.

The log lives in the process that makes the calls. Chat runs in its own
subprocess, so `chat_harness` writes `chat_usage.json` out of it and `run_task`
folds that into the trial envelope, the same way harbor's own usage is folded in.
"""
from __future__ import annotations

import time
from typing import Any

CALL_LOG: list[dict[str, Any]] = []


def reset() -> None:
    CALL_LOG.clear()


def record(model: str, prompt_tokens: int, completion_tokens: int,
           total_tokens: int = 0, started: float | None = None,
           source: str = "") -> None:
    """Append one call. Missing counts are recorded as 0, never guessed."""
    entry = {
        "model": model,
        "prompt_tokens": int(prompt_tokens or 0),
        "completion_tokens": int(completion_tokens or 0),
        "total_tokens": int(total_tokens or 0) or int(prompt_tokens or 0) + int(completion_tokens or 0),
        "source": source,
    }
    # Omit an unknown latency rather than storing None: llm_client aggregates this
    # same list with `c.get("latency_s", 0.0)`, and a present-but-None value makes
    # that sum raise instead of defaulting.
    if started:
        entry["latency_s"] = round(time.time() - started, 3)
    CALL_LOG.append(entry)


def record_response(model: str, response: Any, started: float | None = None,
                    source: str = "") -> None:
    """Append one call from a provider response, if it carries a usage block.

    Handles both the OpenAI chat shape (`prompt_tokens` / `completion_tokens`),
    the Responses shape (`input_tokens` / `output_tokens`) and the Anthropic shape
    (`input_tokens` / `output_tokens` under `usage`). A response with no usage is
    skipped rather than recorded as zero — a zero would understate the total and
    then be priced as free.
    """
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usage")
    if usage is None:
        return

    def field(*names: str) -> int:
        for name in names:
            value = (usage.get(name) if isinstance(usage, dict)
                     else getattr(usage, name, None))
            if isinstance(value, (int, float)):
                return int(value)
        return 0

    prompt = field("prompt_tokens", "input_tokens")
    completion = field("completion_tokens", "output_tokens")
    if not (prompt or completion):
        return
    record(model, prompt, completion, field("total_tokens"), started, source)


def summary() -> dict[str, Any]:
    """Totals across the log, or an empty dict when nothing was recorded."""
    if not CALL_LOG:
        return {}
    latencies = [c["latency_s"] for c in CALL_LOG if c.get("latency_s") is not None]
    return {
        "calls": len(CALL_LOG),
        "prompt_tokens": sum(c["prompt_tokens"] for c in CALL_LOG),
        "completion_tokens": sum(c["completion_tokens"] for c in CALL_LOG),
        "total_tokens": sum(c["total_tokens"] for c in CALL_LOG),
        "latency_s": round(sum(latencies), 3) if latencies else None,
        "source": "call_log",
    }
