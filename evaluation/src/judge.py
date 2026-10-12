"""Resolve the benchmark's LLM judge — one precedence chain, used everywhere.

The judge is a property of the *benchmark*, not of the arm under test: every arm
has to be scored by the same judge or the scores mean nothing next to each other.
So the default lives in ``evaluation/configs/judge.json`` rather than being
repeated in each arm config, and both the runner and the suite preflight resolve
it through this module - preflight checking a different judge than run_task uses
is how nine chat trials once spent four minutes each before failing on a missing
key the check had not looked for.

Precedence, highest first:

1. ``ADHERENCE_JUDGE_MODEL`` / ``ADHERENCE_JUDGE_PROVIDER`` /
   ``ADHERENCE_JUDGE_BASE_URL`` - a per-run override;
2. ``judge_model`` / ``judge_provider`` / ``judge_base_url`` in the arm config -
   a per-arm override, for an arm that must be judged differently;
3. ``evaluation/configs/judge.json`` - the benchmark default;
4. a built-in fallback, so a checkout with no judge.json still runs.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, NamedTuple

_CONFIGS = Path(__file__).resolve().parent.parent / "configs"
_JUDGE_CONFIG = _CONFIGS / "judge.json"

FALLBACK_MODEL = "gpt-5.6-luna"
FALLBACK_PROVIDER = "openai"


class Judge(NamedTuple):
    model: str
    provider: str
    base_url: str
    source: str  # where the model came from, for diagnostics


def _benchmark_default() -> dict[str, Any]:
    try:
        loaded = json.loads(_JUDGE_CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def infer_provider(model: str) -> str:
    """Provider a bare judge model id belongs to. Mirrors llm_client."""
    lowered = (model or "").strip().lower()
    if lowered.startswith(("gpt-", "o1", "o3")):
        return "openai"
    if lowered.startswith("gemini"):
        return "gemini"
    try:
        import openai_compat

        compatible = openai_compat.provider_for_model(lowered)
        if compatible:
            return compatible
    except ImportError:
        pass
    return "anthropic"


def resolve(arm_config: dict[str, Any] | None = None,
            env: dict | None = None) -> Judge:
    """Return the judge for a run. See the module docstring for precedence."""
    scope = os.environ if env is None else env
    arm = arm_config or {}
    default = _benchmark_default()

    model = (str(scope.get("ADHERENCE_JUDGE_MODEL", "")).strip()
             or str(arm.get("judge_model", "") or "").strip()
             or str(default.get("model", "") or "").strip()
             or FALLBACK_MODEL)
    if str(scope.get("ADHERENCE_JUDGE_MODEL", "")).strip():
        source = "ADHERENCE_JUDGE_MODEL"
    elif str(arm.get("judge_model", "") or "").strip():
        source = "arm config"
    elif str(default.get("model", "") or "").strip():
        source = "configs/judge.json"
    else:
        source = "built-in fallback"

    # A provider is only inferred from the model when nobody named one, so an
    # explicit choice is never second-guessed.
    provider = (str(scope.get("ADHERENCE_JUDGE_PROVIDER", "")).strip()
                or str(arm.get("judge_provider", "") or "").strip()
                or (str(default.get("provider", "") or "").strip()
                    if source == "configs/judge.json" else "")
                or infer_provider(model))

    base_url = (str(scope.get("ADHERENCE_JUDGE_BASE_URL", "")).strip()
                or str(arm.get("judge_base_url", "") or "").strip()
                or str(default.get("base_url", "") or "").strip())

    return Judge(model=model, provider=provider.lower(), base_url=base_url,
                 source=source)
