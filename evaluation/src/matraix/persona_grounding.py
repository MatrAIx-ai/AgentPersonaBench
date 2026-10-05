"""Persona dimension grounding: heuristics + optional LLM judge."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Counterfactual cues when probing dimensions.age_bracket (catalog values).
AGE_BRACKET_COUNTERFACTUAL: dict[str, list[str]] = {
    "18-24": [
        r"\bempty nester\b",
        r"\bretired\b",
        r"\bretirement\b",
        r"\bgrand(?:child|children|kids)\b",
        r"\bpension\b",
        r"\bmedicare\b",
        r"\bsenior citizen\b",
        r"\bfor (?:over )?\d{2,3} years\b",
        r"\bdecades (?:in|of)\b",
        r"\bnearing retirement\b",
        r"\baarp\b",
        r"\bmy (?:adult )?children\b",
        r"\bwhen I was your age\b",
    ],
    "25-34": [
        r"\bretired\b",
        r"\bretirement\b",
        r"\bgrand(?:child|children|kids)\b",
        r"\bpension\b",
        r"\bmedicare\b",
        r"\bsenior citizen\b",
        r"\bnearing retirement\b",
        r"\baarp\b",
    ],
    "35-44": [
        r"\bretired\b",
        r"\bmedicare\b",
        r"\bsenior citizen\b",
        r"\bgrand(?:child|children|kids)\b",
        r"\baarp\b",
    ],
    "45-54": [
        r"\bcollege freshman\b",
        r"\bjust graduated (?:high school|college)\b",
        r"\bstill in (?:high )?school\b",
        r"\bdorm room\b",
    ],
    "55-64": [
        r"\bcollege freshman\b",
        r"\bstill in (?:high )?school\b",
        r"\bdorm room\b",
        r"\bmy parents (?:pay|cover)\b",
    ],
    "65+": [
        r"\bcollege freshman\b",
        r"\bstill in (?:high )?school\b",
        r"\bdorm room\b",
        r"\bmy parents (?:pay|cover)\b",
        r"\bfinals week\b",
    ],
}

# Back-compat alias for tests.
AGE_GROUP_COUNTERFACTUAL = AGE_BRACKET_COUNTERFACTUAL


@dataclass
class GroundingResult:
    probe_dimension: str
    probe_value: str
    dim_grounding: float
    counterfactual: bool
    method: str
    matched_cues: list[str] = field(default_factory=list)
    rationale: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def get_nested(data: dict[str, Any], dotted_path: str) -> Any:
    current: Any = data
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def extract_survey_text(survey: dict[str, Any]) -> str:
    parts: list[str] = []
    for entry in survey.get("responses") or []:
        if isinstance(entry, dict):
            answer = entry.get("answer")
            if isinstance(answer, str):
                parts.append(answer)
    summary = survey.get("summary")
    if isinstance(summary, str):
        parts.append(summary)
    return "\n".join(parts)


def heuristic_dim_grounding(
    *,
    probe_dimension: str,
    probe_value: str,
    survey_text: str,
) -> GroundingResult:
    """Fast trial-level check for obvious counterfactual language."""
    matched: list[str] = []
    if probe_dimension in ("dimensions.age_bracket", "demographics.age_group"):
        patterns = AGE_BRACKET_COUNTERFACTUAL.get(probe_value, [])
        for pattern in patterns:
            if re.search(pattern, survey_text, flags=re.IGNORECASE):
                matched.append(pattern)

    counterfactual = bool(matched)
    return GroundingResult(
        probe_dimension=probe_dimension,
        probe_value=probe_value,
        dim_grounding=0.0 if counterfactual else 1.0,
        counterfactual=counterfactual,
        method="heuristic",
        matched_cues=matched,
        rationale=(
            "Counterfactual cues detected for persona value on probe dimension."
            if counterfactual
            else "No obvious counterfactual cues."
        ),
    )


def build_llm_prompt(
    *,
    probe_dimension: str,
    probe_value: str,
    persona: dict[str, Any],
    survey_text: str,
) -> str:
    persona_yaml = yaml.safe_dump(persona, sort_keys=False, allow_unicode=True)
    return f"""You judge whether survey responses are grounded in a fixed persona dimension.

Probe dimension (must be reflected in responses):
  {probe_dimension} = {probe_value!r}

Full persona profile (other dimensions may vary):
```yaml
{persona_yaml}```

Survey responses:
```
{survey_text}
```

Score dim_grounding from 0.0 to 1.0:
- 1.0 = responses plausibly reflect the target dimension; no counterfactual age/life-stage cues
- 0.0 = clearly counterfactual (e.g. target age 18-24 but text reads retired/empty-nester/grandparent)

Return JSON only:
{{"dim_grounding": <float>, "counterfactual": <bool>, "rationale": "<one sentence>"}}
"""


def llm_dim_grounding(
    *,
    probe_dimension: str,
    probe_value: str,
    persona: dict[str, Any],
    survey_text: str,
    model: str = "anthropic/claude-sonnet-4-6",
) -> GroundingResult:
    """LLM judge for dimension grounding (host-side job eval)."""
    try:
        import litellm
    except ImportError as exc:
        return GroundingResult(
            probe_dimension=probe_dimension,
            probe_value=probe_value,
            dim_grounding=0.0,
            counterfactual=False,
            method="llm",
            error=f"litellm not installed: {exc}",
        )

    prompt = build_llm_prompt(
        probe_dimension=probe_dimension,
        probe_value=probe_value,
        persona=persona,
        survey_text=survey_text,
    )
    try:
        response = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        payload = json.loads(content)
        score = float(payload.get("dim_grounding", 0.0))
        score = max(0.0, min(1.0, score))
        return GroundingResult(
            probe_dimension=probe_dimension,
            probe_value=probe_value,
            dim_grounding=score,
            counterfactual=bool(payload.get("counterfactual", score < 0.5)),
            method="llm",
            rationale=str(payload.get("rationale", "")),
        )
    except Exception as exc:  # noqa: BLE001 — surface judge failures in report
        return GroundingResult(
            probe_dimension=probe_dimension,
            probe_value=probe_value,
            dim_grounding=0.0,
            counterfactual=False,
            method="llm",
            error=str(exc),
        )


def load_persona_yaml(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Persona YAML must be a mapping: {path}")
    return raw


def discover_trial_dirs(job_dir: Path) -> list[Path]:
    trials: list[Path] = []
    for child in sorted(job_dir.iterdir()):
        if not child.is_dir():
            continue
        if (child / "result.json").is_file():
            trials.append(child)
    return trials


def resolve_probe_value(
    *,
    probe_dimension: str,
    persona: dict[str, Any] | None,
    env_probe_value: str | None = None,
) -> str:
    if env_probe_value:
        return env_probe_value
    if persona is not None:
        value = get_nested(persona, probe_dimension)
        if value is not None:
            return str(value)
    return ""


def load_trial_grounding(trial_dir: Path) -> dict[str, Any]:
    """Load trial-level grounding already produced by the task verifier."""
    trial_name = trial_dir.name
    grounding_path = trial_dir / "verifier" / "grounding.json"
    reward_path = trial_dir / "verifier" / "reward.txt"
    meta_path = trial_dir / "persona_meta.json"

    report: dict[str, Any] = {
        "trial": trial_name,
        "persona_id": None,
        "schema_reward": None,
        "grounding": None,
        "final_dim_grounding": None,
        "counterfactual": None,
    }

    if reward_path.is_file():
        try:
            report["schema_reward"] = float(reward_path.read_text().strip())
        except ValueError:
            report["schema_reward"] = None

    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        report["persona_id"] = meta.get("persona_id")

    if not grounding_path.is_file():
        report["error"] = (
            f"Missing {grounding_path.relative_to(trial_dir)}; "
            "task verifier must write grounding.json per trial"
        )
        return report

    grounding = json.loads(grounding_path.read_text(encoding="utf-8"))
    report["grounding"] = grounding

    if grounding.get("skipped"):
        report["error"] = str(grounding.get("reason", "grounding skipped"))
        return report

    report["probe_dimension"] = grounding.get("probe_dimension")
    report["probe_value"] = grounding.get("probe_value")
    report["final_dim_grounding"] = grounding.get("dim_grounding")
    report["counterfactual"] = grounding.get("counterfactual")
    report["rationale"] = grounding.get("rationale")
    return report


def evaluate_trial(
    trial_dir: Path,
    *,
    probe_dimension: str | None = None,
    probe_value: str | None = None,
    repo_root: Path | None = None,
    use_llm: bool = False,
    llm_model: str = "anthropic/claude-sonnet-4-6",
) -> dict[str, Any]:
    """Deprecated alias: grounding is computed in the trial verifier, not here."""
    del probe_dimension, probe_value, repo_root, use_llm, llm_model
    loaded = load_trial_grounding(trial_dir)
    # Back-compat for reports that still expect a "heuristic" key.
    if loaded.get("grounding") is not None:
        loaded["heuristic"] = loaded["grounding"]
    loaded["llm"] = None
    return loaded


def build_job_grounding_report(
    trial_reports: list[dict[str, Any]],
    *,
    job_meta: dict[str, Any],
) -> dict[str, Any]:
    probe = job_meta.get("probe", {})
    dimension = probe.get("dimension", "")
    fixed_value = probe.get("value")
    scores = [
        r["final_dim_grounding"]
        for r in trial_reports
        if r.get("final_dim_grounding") is not None
    ]
    counterfactual_count = sum(
        1 for r in trial_reports if r.get("counterfactual") is True
    )
    n = len(scores)
    mean = sum(scores) / n if n else 0.0
    pass_rate = sum(1 for s in scores if s >= 0.5) / n if n else 0.0

    probe_label = (
        f"{dimension}={fixed_value!r}" if fixed_value is not None else dimension
    )
    if mean >= 0.8 and counterfactual_count == 0:
        conclusion = (
            f"Agents appear grounded in {probe_label} (mean dim_grounding={mean:.2f})."
        )
    elif counterfactual_count > 0:
        conclusion = (
            f"{counterfactual_count}/{len(trial_reports)} trials show counterfactual cues "
            f"for {probe_label}; schema-only pass is misleading."
        )
    else:
        conclusion = (
            f"Mixed grounding (mean={mean:.2f}); review individual trial rationales."
        )

    return {
        "job_slug": job_meta.get("job_slug"),
        "probe": probe,
        "n_trials": len(trial_reports),
        "dim_grounding_mean": mean,
        "dim_grounding_pass_rate": pass_rate,
        "counterfactual_rate": counterfactual_count / len(trial_reports)
        if trial_reports
        else 0.0,
        "conclusion": conclusion,
        "trials": trial_reports,
    }
