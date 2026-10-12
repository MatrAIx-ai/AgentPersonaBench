"""Structured trial evaluation artifacts and job-level aggregation."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tomllib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

TRIAL_EVAL_FILENAME = "structured_output.json"
JOB_AGGREGATION_FILENAME = "aggregation.json"
REPORTING_STATUS_FILENAME = "reporting_status.json"
SCHEMA_VERSION = "1.0"
FIELD_KINDS = frozenset({"numerical", "categorical", "textual"})
SUMMARY_GROUP_BY_MODES = frozenset({"none", "categorical", "numeric_band", "persona_attribute"})
JUDGE_GROUP_BY_MODES = SUMMARY_GROUP_BY_MODES
REPORTING_LLM_ENABLE_ENV = "PLAYGROUND_REPORTING_ENABLE_LLM"
REPORTING_LLM_MODEL_ENV = "PLAYGROUND_REPORTING_LLM_MODEL"
DEFAULT_REPORTING_LLM_MODEL = "openai/gpt-4o-mini"
# High-cardinality categorical group-bys (e.g. course titles) can produce
# hundreds of buckets; one JSON completion cannot reliably cover them all.
SUMMARY_LLM_BUCKET_CHUNK = 30
SUMMARY_LLM_SAMPLE_LIMIT = 2
SUMMARY_LLM_SAMPLE_CHARS = 400
# Discrete selected-item titles (course/book/product names). Always exact-count;
# never TF-IDF theme-cluster even when verifiers historically tagged them textual.
DISCRETE_SUBJECT_LABEL_FACET_KEYS = frozenset(
    {
        "decision_subject_label",
        "artifact_subject_label",
    }
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def trial_evaluation_artifact_path(trial_dir: Path) -> Path:
    return trial_dir / "verifier" / TRIAL_EVAL_FILENAME


def job_aggregation_artifact_path(job_dir: Path) -> Path:
    return job_dir / JOB_AGGREGATION_FILENAME


def reporting_status_artifact_path(job_dir: Path) -> Path:
    return job_dir / REPORTING_STATUS_FILENAME


def read_trial_evaluation_artifact(trial_dir: Path) -> dict[str, Any] | None:
    path = trial_evaluation_artifact_path(trial_dir)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    return payload if isinstance(payload, dict) else None


def read_job_aggregation_artifact(job_dir: Path) -> dict[str, Any] | None:
    path = job_aggregation_artifact_path(job_dir)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    return payload if isinstance(payload, dict) else None


def iter_job_trial_dirs(job_dir: Path) -> list[Path]:
    """Trial directories under a job (excludes bookkeeping folders)."""
    if not job_dir.is_dir():
        return []
    return sorted(
        [
            path
            for path in job_dir.iterdir()
            if path.is_dir()
            and path.name not in {"_inputs", "_generated"}
            and not path.name.startswith(".")
        ]
    )


def cheap_job_coverage(job_dir: Path) -> dict[str, int]:
    """Coverage counts from directory layout + result.json presence only."""
    trial_dirs = iter_job_trial_dirs(job_dir)
    completed = sum(1 for path in trial_dirs if (path / "result.json").is_file())
    trial_count = len(trial_dirs)
    return {
        "trialCount": trial_count,
        "completedTrials": completed,
        "pendingTrials": trial_count - completed,
    }


def job_aggregation_artifact_is_fresh(
    job_dir: Path,
    payload: dict[str, Any] | None,
) -> bool:
    """True when cached aggregation coverage still matches disk (no eval reads)."""
    if not isinstance(payload, dict):
        return False
    coverage = payload.get("coverage")
    if not isinstance(coverage, dict):
        return False
    live = cheap_job_coverage(job_dir)
    if live["trialCount"] <= 0:
        return False
    try:
        return (
            int(coverage.get("trialCount")) == live["trialCount"]
            and int(coverage.get("completedTrials")) == live["completedTrials"]
            and int(coverage.get("pendingTrials")) == live["pendingTrials"]
        )
    except (TypeError, ValueError):
        return False


def read_reporting_status_artifact(job_dir: Path) -> dict[str, Any] | None:
    path = reporting_status_artifact_path(job_dir)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    return payload if isinstance(payload, dict) else None


def write_job_aggregation(job_dir: Path, payload: dict[str, Any]) -> None:
    path = job_aggregation_artifact_path(job_dir)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_reporting_status_artifact(job_dir: Path, payload: dict[str, Any]) -> None:
    path = reporting_status_artifact_path(job_dir)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_job_aggregation(
    job_dir: Path,
    *,
    repo_root: Path | None = None,
    llm_client: Any | None = None,
    enable_llm: bool | None = None,
) -> dict[str, Any] | None:
    if not job_dir.is_dir():
        return None

    previous_payload = read_job_aggregation_artifact(job_dir)
    trial_dirs = iter_job_trial_dirs(job_dir)
    if not trial_dirs:
        return None

    field_meta: dict[str, dict[str, Any]] = {}
    field_values: dict[str, list[dict[str, Any]]] = {}
    context_meta: dict[str, dict[str, Any]] = {}
    context_facet_keys: dict[str, list[str]] = {}
    reporting_cache: dict[str, dict[str, Any]] = {}
    stratify_cache: dict[str, list[str]] = {}
    stratify_fields: list[str] = []
    persona_profile_cache: dict[str, dict[str, Any]] = {}
    persona_dimensions_by_id: dict[str, dict[str, Any]] = {}
    trial_count = len(trial_dirs)
    completed_trials = 0
    artifact_ready_trials = 0
    completed_without_artifact = 0
    pending_trials = 0

    for trial_dir in trial_dirs:
        completed = (trial_dir / "result.json").is_file()
        if completed:
            completed_trials += 1
        else:
            pending_trials += 1

        artifact = read_trial_evaluation_artifact(trial_dir)
        artifact = _enrich_trial_evaluation_with_user_feedback(
            artifact,
            trial_dir=trial_dir,
            repo_root=repo_root,
        )
        passed = False
        if isinstance(artifact, dict):
            presence = artifact.get("presenceCheck")
            if isinstance(presence, dict):
                passed = bool(presence.get("passed"))
            else:
                passed = True
        if not artifact or not passed:
            if completed:
                completed_without_artifact += 1
            continue

        artifact_ready_trials += 1
        persona_id = _trial_persona_id(trial_dir)
        if persona_id and persona_id not in persona_dimensions_by_id:
            persona_dimensions_by_id[persona_id] = _trial_persona_dimensions(
                trial_dir,
                repo_root=repo_root,
                cache=persona_profile_cache,
            )
        reporting_config = _load_task_reporting_config(
            trial_dir=trial_dir,
            repo_root=repo_root,
            cache=reporting_cache,
        )
        for dimension in _load_task_stratify_fields(
            trial_dir=trial_dir,
            repo_root=repo_root,
            cache=stratify_cache,
        ):
            if dimension not in stratify_fields:
                stratify_fields.append(dimension)
        for context in _iter_contexts(artifact):
            context_key = str(context.get("key") or "").strip()
            if not context_key:
                continue
            resolved_summary_directives = _resolve_summary_directives(
                context=context,
                reporting_config=reporting_config,
            )
            resolved_judge_directives = _resolve_judge_directives(
                context=context,
                reporting_config=reporting_config,
            )
            resolved_distribution_directives = _resolve_distribution_directives(
                context=context,
                reporting_config=reporting_config,
            )
            if context_key not in context_meta:
                context_meta[context_key] = {
                    "key": context_key,
                    "label": context.get("label") or context_key,
                    "contextType": context.get("contextType") or "grouped_fields",
                    "questionType": context.get("questionType"),
                    "scaleMin": context.get("scaleMin"),
                    "scaleMax": context.get("scaleMax"),
                    "scaleLabels": context.get("scaleLabels"),
                    "summaryAnalyses": resolved_summary_directives,
                    "signalScans": resolved_judge_directives,
                    "distributions": resolved_distribution_directives,
                }
            else:
                if resolved_summary_directives and not context_meta[context_key].get("summaryAnalyses"):
                    context_meta[context_key]["summaryAnalyses"] = resolved_summary_directives
                if resolved_judge_directives and not context_meta[context_key].get("signalScans"):
                    context_meta[context_key]["signalScans"] = resolved_judge_directives
                if resolved_distribution_directives and not context_meta[context_key].get("distributions"):
                    context_meta[context_key]["distributions"] = resolved_distribution_directives
                if not context_meta[context_key].get("questionType") and context.get("questionType"):
                    context_meta[context_key]["questionType"] = context.get("questionType")
                if context_meta[context_key].get("scaleMin") is None and context.get("scaleMin") is not None:
                    context_meta[context_key]["scaleMin"] = context.get("scaleMin")
                if context_meta[context_key].get("scaleMax") is None and context.get("scaleMax") is not None:
                    context_meta[context_key]["scaleMax"] = context.get("scaleMax")
                if not context_meta[context_key].get("scaleLabels") and context.get("scaleLabels"):
                    context_meta[context_key]["scaleLabels"] = context.get("scaleLabels")
            for facet in _iter_facets(context):
                facet_key = str(facet.get("key") or "").strip()
                kind = str(facet.get("kind") or "").strip().lower()
                if not facet_key or kind not in FIELD_KINDS:
                    continue
                qualified_key = "{}.{}".format(context_key, facet_key)
                if qualified_key not in field_meta:
                    field_meta[qualified_key] = {
                        "key": qualified_key,
                        "facetKey": facet_key,
                        "contextKey": context_key,
                        "contextLabel": context_meta[context_key]["label"],
                        "label": facet.get("label") or facet_key,
                        "kind": kind,
                        "role": facet.get("role"),
                        "explainsFacetKey": facet.get("explainsFacetKey"),
                        "group": context_key,
                        "description": facet.get("description"),
                        "unit": facet.get("unit"),
                        "higherIsBetter": facet.get("higherIsBetter"),
                        "categories": facet.get("categories"),
                        "order": facet.get("order"),
                        "scaleMin": facet.get("scaleMin"),
                        "scaleMax": facet.get("scaleMax"),
                    }
                else:
                    existing = field_meta[qualified_key]
                    if not existing.get("categories") and facet.get("categories"):
                        existing["categories"] = facet.get("categories")
                    if existing.get("scaleMin") is None and facet.get("scaleMin") is not None:
                        existing["scaleMin"] = facet.get("scaleMin")
                    if existing.get("scaleMax") is None and facet.get("scaleMax") is not None:
                        existing["scaleMax"] = facet.get("scaleMax")
                    if not existing.get("role") and facet.get("role"):
                        existing["role"] = facet.get("role")
                    if not existing.get("explainsFacetKey") and facet.get("explainsFacetKey"):
                        existing["explainsFacetKey"] = facet.get("explainsFacetKey")
                    # Prefer primary over score/evidence when schema marks a hero rating.
                    if facet.get("role") == "primary":
                        existing["role"] = "primary"
                # A declared binding is authoritative for role: a textual facet that
                # explains another field is an explanation, regardless of its name.
                meta_entry = field_meta[qualified_key]
                if kind == "textual" and meta_entry.get("explainsFacetKey"):
                    meta_entry["role"] = "explanation"
                context_facet_keys.setdefault(context_key, [])
                if qualified_key not in context_facet_keys[context_key]:
                    context_facet_keys[context_key].append(qualified_key)
                field_values.setdefault(qualified_key, []).append(
                    {
                        "trialName": trial_dir.name,
                        "personaId": persona_id,
                        "value": facet.get("value"),
                    }
                )

    fields = [
        _aggregate_field(
            meta=field_meta[key],
            values=field_values.get(key, []),
            artifact_ready_trials=artifact_ready_trials,
        )
        for key in sorted(field_meta)
    ]
    _enrich_user_feedback_field_meta(field_meta)
    _enrich_rating_scale_field_meta(field_meta)
    # Re-apply enrichment onto already-built field payloads.
    for field in fields:
        key = str(field.get("key") or "")
        enriched = field_meta.get(key)
        if not enriched:
            continue
        for attr in ("categories", "scaleMin", "scaleMax", "role"):
            if enriched.get(attr) is None:
                continue
            field[attr] = enriched.get(attr)
    fields_by_key = {field["key"]: field for field in fields}
    _enrich_survey_context_meta_from_questionnaire(
        context_meta,
        job_dir=job_dir,
        repo_root=repo_root,
    )
    contexts = [
        _aggregate_context(
            meta=context_meta[key],
            facet_keys=context_facet_keys.get(key, []),
            fields_by_key=fields_by_key,
            field_values=field_values,
            persona_dimensions=persona_dimensions_by_id,
            stratify_fields=stratify_fields,
        )
        for key in sorted(context_meta)
    ]
    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "artifactType": "job_aggregation",
        "generatedAt": _utc_now(),
        "coverage": {
            "trialCount": trial_count,
            "completedTrials": completed_trials,
            "pendingTrials": pending_trials,
            "artifactReadyTrials": artifact_ready_trials,
            "completedWithoutArtifactTrials": completed_without_artifact,
        },
        "fields": fields,
        "contexts": contexts,
    }
    payload = _apply_llm_reporting(
        payload=payload,
        previous_payload=previous_payload,
        llm_client=llm_client,
        enable_llm=enable_llm,
    )
    payload["reporting"] = _build_reporting_view(payload)
    write_job_aggregation(job_dir, payload)
    return payload


def _enrich_trial_evaluation_with_user_feedback(
    artifact: dict[str, Any] | None,
    *,
    trial_dir: Path,
    repo_root: Path | None,
) -> dict[str, Any] | None:
    if not isinstance(artifact, dict):
        return artifact
    contexts = artifact.get("contexts")
    if isinstance(contexts, list):
        for context in contexts:
            if not isinstance(context, dict):
                continue
            if str(context.get("contextType") or "").strip() == "user_feedback":
                return artifact
    raw_feedback, artifact_path = _read_user_feedback_artifact(trial_dir)
    if raw_feedback is None:
        return artifact
    task_path = _task_path_from_trial_config(trial_dir)
    feedback_context = _synthesized_user_feedback_context(
        raw_feedback,
        task_path=task_path,
        repo_root=repo_root,
    )
    if feedback_context is None:
        return artifact
    enriched = dict(artifact)
    enriched_contexts = list(contexts) if isinstance(contexts, list) else []
    enriched_contexts.append(feedback_context)
    enriched["contexts"] = enriched_contexts
    source_artifacts = dict(enriched.get("sourceArtifacts") or {})
    if artifact_path is not None and "userFeedback" not in source_artifacts:
        source_artifacts["userFeedback"] = str(artifact_path)
    if source_artifacts:
        enriched["sourceArtifacts"] = source_artifacts
    return enriched


def _trial_persona_id(trial_dir: Path) -> str | None:
    config_path = trial_dir / "config.json"
    if not config_path.is_file():
        return None
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    agent = payload.get("agent")
    if not isinstance(agent, dict):
        return None
    kwargs = agent.get("kwargs")
    if not isinstance(kwargs, dict):
        return None
    persona_path = str(kwargs.get("persona_path") or "").strip()
    if not persona_path:
        return None
    stem = Path(persona_path).stem
    if stem.startswith("persona_"):
        return stem[len("persona_") :]
    return stem or None


def _trial_persona_path(trial_dir: Path) -> str | None:
    config_path = trial_dir / "config.json"
    if not config_path.is_file():
        return None
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    agent = payload.get("agent")
    kwargs = agent.get("kwargs") if isinstance(agent, dict) else None
    if not isinstance(kwargs, dict):
        return None
    persona_path = str(kwargs.get("persona_path") or "").strip()
    return persona_path or None


def _trial_persona_dimensions(
    trial_dir: Path,
    *,
    repo_root: Path | None,
    cache: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Load the persona profile `dimensions` map (age_bracket, life_stage, …).

    Used for the customer-insight reporting lens (`groupByMode: persona_attribute`)
    so analyses can be sliced by who the persona is, not only by task outcome.
    """
    persona_path = _trial_persona_path(trial_dir)
    if not persona_path or repo_root is None:
        return {}
    cached = cache.get(persona_path)
    if cached is not None:
        return cached
    resolved = (repo_root / persona_path).resolve()
    dimensions: dict[str, Any] = {}
    if resolved.is_file():
        try:
            import yaml

            raw = yaml.safe_load(resolved.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and isinstance(raw.get("dimensions"), dict):
                dimensions = {str(k): v for k, v in raw["dimensions"].items() if v is not None}
        except Exception:  # noqa: BLE001
            dimensions = {}
    cache[persona_path] = dimensions
    return dimensions


def _iter_fields(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    fields = artifact.get("fields")
    if not isinstance(fields, list):
        return []
    return [item for item in fields if isinstance(item, dict)]


def _iter_contexts(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    contexts = artifact.get("contexts")
    if isinstance(contexts, list):
        return [item for item in contexts if isinstance(item, dict)]

    # Backward-compatible fallback for early adopters that only wrote fields + group.
    grouped: dict[str, dict[str, Any]] = {}
    for field in _iter_fields(artifact):
        key = str(field.get("key") or "").strip()
        if not key:
            continue
        group = str(field.get("group") or key).strip()
        item = grouped.setdefault(
            group,
            {
                "key": group,
                "label": group,
                "contextType": "grouped_fields",
                "facets": [],
            },
        )
        item["facets"].append(
            {
                "key": key.split(".")[-1],
                "label": field.get("label") or key,
                "kind": field.get("kind"),
                "role": field.get("role"),
                "value": field.get("value"),
                "description": field.get("description"),
                "unit": field.get("unit"),
                "higherIsBetter": field.get("higherIsBetter"),
                "categories": field.get("categories"),
                "order": field.get("order"),
            }
        )
    return list(grouped.values())


def _iter_facets(context: dict[str, Any]) -> list[dict[str, Any]]:
    facets = context.get("facets")
    if not isinstance(facets, list):
        return []
    return [item for item in facets if isinstance(item, dict)]


def _iter_summary_directives(context: dict[str, Any]) -> list[dict[str, Any]]:
    directives = context.get("summaryAnalyses")
    if not isinstance(directives, list):
        return []
    return [item for item in directives if isinstance(item, dict)]


def _iter_judge_directives(context: dict[str, Any]) -> list[dict[str, Any]]:
    directives = context.get("signalScans")
    if not isinstance(directives, list):
        return []
    return [item for item in directives if isinstance(item, dict)]


def _iter_distribution_directives(source: dict[str, Any]) -> list[dict[str, Any]]:
    directives = source.get("distributions")
    if not isinstance(directives, list):
        return []
    return [item for item in directives if isinstance(item, dict)]


def _distribution_directive_dedupe_marker(directive: dict[str, Any]) -> str:
    """Unique key so the same facet can appear as standalone AND as a persona cross."""
    facet_key = str(directive.get("facetKey") or "").strip()
    if directive.get("standalone") is True:
        return "{}|standalone".format(facet_key)
    if "groupByPersonaDimensions" in directive:
        raw = directive.get("groupByPersonaDimensions")
        if isinstance(raw, list):
            dims = [str(item).strip() for item in raw if str(item).strip()]
            if not dims:
                return "{}|standalone".format(facet_key)
            return "{}|{}".format(facet_key, ",".join(dims))
        return "{}|standalone".format(facet_key)
    single = str(directive.get("groupByPersonaDimension") or "").strip()
    if single:
        return "{}|{}".format(facet_key, single)
    # Omitted axes → later filled from sampling.fields; keep one default slot.
    return "{}|default".format(facet_key)


def _resolve_distribution_directives(
    *,
    context: dict[str, Any],
    reporting_config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Author-declared persona cards for a context (standalone and/or crosses).

    Declared in ``reporting.json`` (``contextRules[]`` → ``distributions[]``, or
    inline on the verifier context). Each directive names a ``facetKey``.
    ``groupByPersonaDimensions: []`` / ``standalone: true`` → cohort-level card;
    a non-empty list → persona cross-tab; omitted axes default to sampling.fields.
    """
    context_key = str(context.get("key") or "").strip()
    context_type = str(context.get("contextType") or "").strip()
    resolved: list[dict[str, Any]] = list(_iter_distribution_directives(context))
    for rule in reporting_config.get("contextRules") or []:
        if isinstance(rule, dict) and _rule_matches_context(
            rule, context_key=context_key, context_type=context_type
        ):
            resolved.extend(_iter_distribution_directives(rule))
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for directive in resolved:
        if not isinstance(directive, dict):
            continue
        facet_key = str(directive.get("facetKey") or "").strip()
        if not facet_key:
            continue
        marker = _distribution_directive_dedupe_marker(directive)
        if marker in seen:
            continue
        seen.add(marker)
        deduped.append(directive)
    return deduped


def _load_task_reporting_config(
    *,
    trial_dir: Path,
    repo_root: Path | None,
    cache: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    task_path = _task_path_from_trial_config(trial_dir)
    if not task_path or repo_root is None:
        return {}
    cached = cache.get(task_path)
    if cached is not None:
        return cached
    task_dir = (repo_root / task_path).resolve()
    for candidate in (task_dir / "reporting.json", task_dir / "reporting.toml"):
        if not candidate.is_file():
            continue
        try:
            if candidate.suffix == ".json":
                payload = json.loads(candidate.read_text(encoding="utf-8"))
            else:
                payload = tomllib.loads(candidate.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            payload = {}
        if isinstance(payload, dict):
            cache[task_path] = payload
            return payload
    cache[task_path] = {}
    return {}


def _load_task_stratify_fields(
    *,
    trial_dir: Path,
    repo_root: Path | None,
    cache: dict[str, list[str]],
) -> list[str]:
    """Default persona axes for the cross-tab lens (persona_strategy.json).

    Uses ``sampling.fields`` — the dimensions the cohort was balanced across.
    When a strategy declares no stratify fields, falls back to the keys of
    ``dimensionFilters`` so a distribution directive without explicit axes still
    resolves to meaningful segments.
    """
    task_path = _task_path_from_trial_config(trial_dir)
    if not task_path or repo_root is None:
        return []
    cached = cache.get(task_path)
    if cached is not None:
        return cached
    strategy_path = (repo_root / task_path).resolve() / "persona_strategy.json"
    fields: list[str] = []
    if strategy_path.is_file():
        try:
            payload = json.loads(strategy_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            payload = {}
        if isinstance(payload, dict):
            sampling = payload.get("sampling")
            raw = sampling.get("fields") if isinstance(sampling, dict) else None
            if isinstance(raw, list):
                fields = [str(item).strip() for item in raw if str(item).strip()]
            if not fields:
                filters = payload.get("dimensionFilters")
                if isinstance(filters, dict):
                    fields = [str(key).strip() for key in filters if str(key).strip()]
    cache[task_path] = fields
    return fields


def _task_path_from_trial_config(trial_dir: Path) -> str | None:
    config_path = trial_dir / "config.json"
    if not config_path.is_file():
        return None
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    task = payload.get("task")
    if not isinstance(task, dict):
        return None
    path = task.get("path")
    if isinstance(path, str) and path.strip():
        return path.strip().replace("\\", "/")
    return None


def _load_survey_instrument_for_job(
    job_dir: Path,
    *,
    repo_root: Path | None,
) -> Any | None:
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[4]
    for trial_dir in sorted(path for path in job_dir.iterdir() if path.is_dir()):
        task_path = _task_path_from_trial_config(trial_dir)
        if not task_path:
            continue
        questionnaire_path = root / task_path / "input" / "questionnaire.yaml"
        if not questionnaire_path.is_file():
            continue
        try:
            import yaml

            raw = yaml.safe_load(questionnaire_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(raw, dict):
            continue
        try:
            from backend.service.survey_types import SurveyInstrument

            return SurveyInstrument.from_dict(raw)
        except Exception:  # noqa: BLE001
            continue
    return None


def _enrich_survey_context_meta_from_questionnaire(
    context_meta: dict[str, dict[str, Any]],
    *,
    job_dir: Path,
    repo_root: Path | None,
) -> None:
    """Attach prompt/scale metadata from questionnaire.yaml onto question contexts."""
    instrument = _load_survey_instrument_for_job(job_dir, repo_root=repo_root)
    if instrument is None:
        return
    questions = {
        str(getattr(question, "id", "") or "").strip(): question
        for question in getattr(instrument, "questions", []) or []
    }
    for context_key, meta in context_meta.items():
        if not context_key.startswith("question."):
            continue
        question_id = context_key[len("question.") :].strip()
        question = questions.get(question_id)
        if question is None:
            continue
        prompt = str(getattr(question, "prompt", "") or "").strip()
        question_type = str(getattr(question, "type", "") or "").strip().lower()
        label = str(meta.get("label") or "").strip()
        if prompt and (not label or label == question_id or label == context_key):
            meta["label"] = prompt
        if question_type and not meta.get("questionType"):
            meta["questionType"] = question_type
        if question_type == "likert":
            min_value = getattr(question, "min_value", None)
            max_value = getattr(question, "max_value", None)
            if meta.get("scaleMin") is None and min_value is not None:
                meta["scaleMin"] = int(min_value)
            if meta.get("scaleMax") is None and max_value is not None:
                meta["scaleMax"] = int(max_value)
            scale_labels = getattr(question, "scale_labels", None) or getattr(question, "scaleLabels", None)
            if not meta.get("scaleLabels") and isinstance(scale_labels, dict) and scale_labels:
                meta["scaleLabels"] = {
                    str(key): str(value)
                    for key, value in scale_labels.items()
                    if str(value).strip()
                }
        if question_type in {"single_choice", "multi_choice"} and not meta.get("choiceOptions"):
            option_rows: list[dict[str, str]] = []
            details = getattr(question, "option_details", None) or []
            if details:
                for option in details:
                    option_id = str(getattr(option, "id", "") or "").strip()
                    option_label = str(getattr(option, "label", "") or "").strip() or option_id
                    if option_id:
                        option_rows.append({"id": option_id, "label": option_label})
            else:
                for raw_option in getattr(question, "options", []) or []:
                    option_id = str(raw_option or "").strip()
                    if option_id:
                        option_rows.append({"id": option_id, "label": option_id})
            if option_rows:
                meta["choiceOptions"] = option_rows


def _read_user_feedback_artifact(trial_dir: Path) -> tuple[dict[str, Any] | None, Path | None]:
    for candidate in _user_feedback_candidates(trial_dir):
        if not candidate.is_file():
            continue
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if isinstance(payload, dict):
            return payload, candidate
    return None, None


def _user_feedback_candidates(trial_dir: Path) -> list[Path]:
    candidates = [
        trial_dir / "artifacts" / "app" / "output" / "user_feedback.json",
        trial_dir / "verifier" / "user_feedback.json",
        trial_dir / "logs" / "verifier" / "user_feedback.json",
    ]
    tmp_root = trial_dir / "artifacts" / "tmp"
    if tmp_root.is_dir():
        for path in sorted(tmp_root.rglob("user_feedback.json")):
            candidates.append(path)
    return candidates


def _load_self_report_schema_fields(
    task_path: str | None,
    repo_root: Path | None,
) -> list[Any]:
    """Return authored self-report fields (with ``key`` / ``prompt``) for a task.

    Prefer the playground helper when importable; otherwise read
    ``input/self_report_schema.yaml`` directly so aggregation labels still use
    the task prompt even if ``playground`` is not on ``PYTHONPATH``.
    """
    if not task_path or repo_root is None:
        return []
    try:
        from playground.self_report_task_config import (
            load_self_report_schema_for_task_path,
        )

        schema = load_self_report_schema_for_task_path(
            task_path,
            repo_root=repo_root,
            fallback_to_default=False,
        )
        if schema is not None and schema.fields:
            return list(schema.fields)
    except Exception:  # noqa: BLE001 — fall through to YAML
        pass

    candidates = [
        (repo_root / task_path / "input" / "self_report_schema.yaml").resolve(),
        (repo_root / task_path / "self_report_schema.yaml").resolve(),
    ]
    for path in candidates:
        if not path.is_file():
            continue
        try:
            import yaml

            payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(payload, dict):
            continue
        fields: list[Any] = []
        for index, entry in enumerate(payload.get("fields") or []):
            if not isinstance(entry, dict):
                continue
            key = str(entry.get("key") or "").strip()
            prompt = str(entry.get("prompt") or "").strip()
            if not key or not prompt:
                continue
            raw_choices = entry.get("choices") or []
            normalized_choices: list[str] = []
            for choice in raw_choices:
                # YAML 1.1 turns bare yes/no into booleans.
                if isinstance(choice, bool):
                    normalized_choices.append("yes" if choice else "no")
                else:
                    token = str(choice).strip()
                    if token:
                        normalized_choices.append(token)
            lowered = [token.lower() for token in normalized_choices]
            if "partially" in lowered and "true" in lowered and "false" in lowered:
                normalized_choices = [
                    "yes"
                    if token.lower() == "true"
                    else "no"
                    if token.lower() == "false"
                    else token
                    for token in normalized_choices
                ]
            # Minimal duck-typed field for _feedback_facet_from_schema_field.
            fields.append(
                type(
                    "YamlSelfReportField",
                    (),
                    {
                        "key": key,
                        "prompt": prompt,
                        "kind": str(entry.get("kind") or "string").strip() or "string",
                        "required": True,
                        "minimum": entry.get("minimum"),
                        "maximum": entry.get("maximum"),
                        "choices": tuple(normalized_choices),
                        "explains": None,
                    },
                )()
            )
            explanation = entry.get("explanation")
            blocks = (
                [explanation]
                if isinstance(explanation, dict)
                else (explanation if isinstance(explanation, list) else [])
            )
            for block in blocks:
                if not isinstance(block, dict):
                    continue
                ekey = str(block.get("key") or "").strip()
                eprompt = str(block.get("prompt") or "").strip()
                if not ekey or not eprompt:
                    continue
                fields.append(
                    type(
                        "YamlSelfReportField",
                        (),
                        {
                            "key": ekey,
                            "prompt": eprompt,
                            "kind": str(block.get("kind") or "string").strip() or "string",
                            "required": True,
                            "minimum": None,
                            "maximum": None,
                            "choices": (),
                            "explains": key,
                        },
                    )()
                )
        if fields:
            return fields
    return []


def _synthesized_user_feedback_context(
    raw_feedback: dict[str, Any],
    *,
    task_path: str | None,
    repo_root: Path | None,
) -> dict[str, Any] | None:
    schema_fields = _load_self_report_schema_fields(task_path, repo_root)
    facets: list[dict[str, Any]] = []
    if schema_fields:
        for field in schema_fields:
            if field.key not in raw_feedback:
                continue
            facet = _feedback_facet_from_schema_field(field, raw_feedback.get(field.key))
            if facet is not None:
                facets.append(facet)
    else:
        for key, value in raw_feedback.items():
            facet = _feedback_facet_from_heuristic(key, value)
            if facet is not None:
                facets.append(facet)
    if not facets:
        return None
    return {
        "key": "user_feedback.primary",
        "label": "User feedback",
        "contextType": "user_feedback",
        "facets": facets,
    }


def _feedback_facet_from_schema_field(field: Any, raw_value: Any) -> dict[str, Any] | None:
    normalized_key = _normalized_feedback_key(str(field.key))
    kind = _feedback_field_kind(str(field.kind))
    value = _coerce_feedback_value(kind, raw_value)
    if not _has_value(value):
        return None
    explains = str(getattr(field, "explains", "") or "").strip()
    facet: dict[str, Any] = {
        "key": normalized_key,
        "label": _feedback_label(normalized_key, prompt=str(field.prompt or "")),
        # A declared binding is the source of truth for role: any textual field
        # that explains another field is an explanation, regardless of its name.
        "role": "explanation" if (explains and kind == "textual") else _feedback_role(normalized_key, kind),
        "kind": kind,
        "value": value,
    }
    if explains:
        facet["explainsFacetKey"] = _normalized_feedback_key(explains)
    choices = tuple(str(choice).strip() for choice in (getattr(field, "choices", ()) or ()) if str(choice).strip())
    if kind == "categorical":
        if choices:
            facet["categories"] = list(choices)
        elif str(getattr(field, "kind", "") or "").strip().lower() == "boolean":
            facet["categories"] = ["true", "false"]
    if kind == "numerical":
        minimum = getattr(field, "minimum", None)
        maximum = getattr(field, "maximum", None)
        if minimum is not None:
            facet["scaleMin"] = int(minimum)
        if maximum is not None:
            facet["scaleMax"] = int(maximum)
    return facet


def _feedback_facet_from_heuristic(raw_key: str, raw_value: Any) -> dict[str, Any] | None:
    normalized_key = _normalized_feedback_key(raw_key)
    kind = _feedback_kind_from_value(normalized_key, raw_value)
    value = _coerce_feedback_value(kind, raw_value)
    if not _has_value(value):
        return None
    facet: dict[str, Any] = {
        "key": normalized_key,
        "label": _feedback_label(normalized_key),
        "role": _feedback_role(normalized_key, kind),
        "kind": kind,
        "value": value,
    }
    if kind == "categorical":
        inventory = _default_feedback_categories(normalized_key, value)
        if inventory:
            facet["categories"] = inventory
    if kind == "numerical" and normalized_key in {
        "overall_experience_rating",
        "trust_level",
        "effort_rating",
    }:
        facet["scaleMin"] = 1
        facet["scaleMax"] = 10
    return facet


def _enrich_user_feedback_field_meta(field_meta: dict[str, dict[str, Any]]) -> None:
    """Normalize chat self-report facet roles/inventories even when trials wrote raw contexts."""
    feedback_fields = [
        meta
        for key, meta in field_meta.items()
        if str(meta.get("contextKey") or "").startswith("user_feedback")
        or str(meta.get("group") or "").startswith("user_feedback")
        or ".user_feedback." in key
        or key.startswith("user_feedback.")
    ]
    if not feedback_fields:
        return

    for meta in feedback_fields:
        facet_key = _normalized_feedback_key(str(meta.get("facetKey") or meta.get("key") or ""))
        kind = str(meta.get("kind") or "").strip().lower()
        # Always prefer the overall rating as the hero signal.
        if facet_key == "overall_experience_rating":
            meta["role"] = "primary"
            if meta.get("scaleMin") is None:
                meta["scaleMin"] = 1
            if meta.get("scaleMax") is None:
                meta["scaleMax"] = 10
            continue
        if kind == "numerical" and facet_key in {"trust_level", "effort_rating"}:
            if meta.get("scaleMin") is None:
                meta["scaleMin"] = 1
            if meta.get("scaleMax") is None:
                meta["scaleMax"] = 10
            if meta.get("role") == "primary":
                meta["role"] = "score"
            continue
        if kind == "categorical":
            if meta.get("role") == "primary":
                meta["role"] = "evidence"
            if not meta.get("categories"):
                inventory = _default_feedback_categories(facet_key, None)
                if inventory is None and "clarification" in facet_key:
                    inventory = ["true", "false"]
                if inventory:
                    meta["categories"] = inventory
        if kind == "textual" and facet_key in {"feedback_reason", "clarifying_notes", "feedback_comments"}:
            meta["role"] = "explanation"


def _enrich_rating_scale_field_meta(field_meta: dict[str, dict[str, Any]]) -> None:
    """Attach known 1–10 scales for rating facets in *any* context.

    ``overall_experience_rating`` can appear under user_feedback or other
    task contexts. Without an explicit scaleMax, the UI used to treat the
    cohort's observed max (e.g. 4) as the full score.
    """
    for key, meta in field_meta.items():
        leaf = _normalized_feedback_key(
            str(meta.get("facetKey") or "").split(".")[-1]
            or str(key).split(".")[-1]
        )
        if leaf not in {"overall_experience_rating", "trust_level", "effort_rating"}:
            continue
        kind = str(meta.get("kind") or "").strip().lower()
        if kind and kind not in {"numerical", "integer"}:
            continue
        if meta.get("scaleMin") is None:
            meta["scaleMin"] = 1
        if meta.get("scaleMax") is None:
            meta["scaleMax"] = 10


def _default_feedback_categories(normalized_key: str, value: Any) -> list[str] | None:
    if normalized_key in {
        "need_constraint_satisfaction",
        "personal_preference_satisfaction",
        "clarity_of_next_step",
    }:
        return ["yes", "partially", "no"]
    if isinstance(value, bool) or str(value).strip().lower() in {"true", "false"}:
        return ["true", "false"]
    if normalized_key in {
        "felt_understood",
        "asked_useful_clarification_questions",
    }:
        return ["true", "false"]
    return None


def _normalized_feedback_key(raw_key: str) -> str:
    alias_map = {
        "needConstraintSatisfaction": "need_constraint_satisfaction",
        "personalPreferenceSatisfaction": "personal_preference_satisfaction",
        "overallExperienceRating": "overall_experience_rating",
        "trustLevel": "trust_level",
        "effortRating": "effort_rating",
        "clarityOfNextStep": "clarity_of_next_step",
        "feltUnderstood": "felt_understood",
        "askedUsefulClarificationQuestions": "asked_useful_clarification_questions",
        "clarifyingNotes": "clarifying_notes",
        "ratingReason": "feedback_reason",
        "comments": "feedback_comments",
    }
    if raw_key in alias_map:
        return alias_map[raw_key]
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(raw_key)).replace("-", "_").lower()
    snake = re.sub(r"__+", "_", snake).strip("_")
    if snake == "reason":
        return "feedback_reason"
    return snake


def _feedback_field_kind(field_kind: str) -> str:
    normalized = field_kind.strip().lower()
    if normalized == "integer":
        return "numerical"
    if normalized in {"enum", "boolean"}:
        return "categorical"
    return "textual"


def _feedback_kind_from_value(normalized_key: str, raw_value: Any) -> str:
    if normalized_key in {
        "overall_experience_rating",
        "trust_level",
        "effort_rating",
        "satisfaction",
        "frustration",
        "ease_of_use",
    }:
        return "numerical"
    if isinstance(raw_value, bool):
        return "categorical"
    if isinstance(raw_value, (int, float)) and not isinstance(raw_value, bool):
        return "numerical"
    if normalized_key.endswith("_satisfaction") or normalized_key.startswith("clarity_"):
        return "categorical"
    if any(token in normalized_key for token in ("reason", "note", "comment", "rationale", "explanation")):
        return "textual"
    return "textual" if isinstance(raw_value, str) else "categorical"


def _coerce_feedback_value(kind: str, raw_value: Any) -> Any:
    if kind == "numerical":
        if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
            return None
        return int(round(float(raw_value)))
    if kind == "categorical":
        if isinstance(raw_value, bool):
            return "true" if raw_value else "false"
        text = str(raw_value or "").strip().lower()
        return text or None
    text = str(raw_value or "").strip()
    return text or None


def _feedback_role(normalized_key: str, kind: str) -> str:
    if normalized_key == "overall_experience_rating":
        return "primary"
    if kind == "numerical":
        return "score"
    if normalized_key == "feedback_reason" or any(
        token in normalized_key for token in ("note", "comment", "rationale", "explanation")
    ):
        return "explanation"
    if normalized_key in {"need_constraint_satisfaction", "personal_preference_satisfaction"}:
        return "evidence"
    return "evidence"


def _feedback_label(normalized_key: str, *, prompt: str = "") -> str:
    """Label for a self-report facet — brainlessly the authored prompt when set."""
    if prompt.strip():
        return prompt.strip()
    return normalized_key.replace("_", " ").strip().title()


def _rule_matches_context(rule: dict[str, Any], *, context_key: str, context_type: str) -> bool:
    match = rule.get("match")
    if not isinstance(match, dict):
        return False
    match_key = str(match.get("key") or "").strip()
    match_type = str(match.get("contextType") or "").strip()
    if match_key and match_key != context_key:
        return False
    if match_type and match_type != context_type:
        return False
    return True


def _tag_directive_lens(directive: dict[str, Any], *, lens: str) -> dict[str, Any]:
    """Copy a directive, stamp its analysis lens, and infer persona grouping.

    A directive that names a persona dimension (`groupByPersonaDimension`) with no
    explicit `groupByMode` defaults to persona-attribute grouping, so authors only
    need to name the dimension. The lens stays Custom (task) regardless.
    """
    tagged = {**directive, "lens": str(directive.get("lens") or lens).strip().lower() or lens}
    if (
        str(tagged.get("groupByPersonaDimension") or "").strip()
        and not str(tagged.get("groupByMode") or "").strip()
    ):
        tagged["groupByMode"] = "persona_attribute"
    return tagged


def _collect_rule_directives(
    rules: Any,
    *,
    context_key: str,
    context_type: str,
    iterator: Any,
    lens: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(rules, list):
        return out
    for rule in rules:
        if not isinstance(rule, dict) or not _rule_matches_context(
            rule, context_key=context_key, context_type=context_type
        ):
            continue
        for directive in iterator(rule):
            if isinstance(directive, dict):
                out.append(_tag_directive_lens(directive, lens=lens))
    return out


def _resolve_directives(
    *,
    context: dict[str, Any],
    reporting_config: dict[str, Any],
    iterator: Any,
) -> list[dict[str, Any]]:
    # Single rule list: contextRules. Summaries and signal scans always render in
    # Custom analysis; a persona-dimension grouping is just an optional axis.
    context_key = str(context.get("key") or "").strip()
    context_type = str(context.get("contextType") or "").strip()
    resolved: list[dict[str, Any]] = [
        _tag_directive_lens(directive, lens="task")
        for directive in iterator(context)
        if isinstance(directive, dict)
    ]
    resolved += _collect_rule_directives(
        reporting_config.get("contextRules"),
        context_key=context_key,
        context_type=context_type,
        iterator=iterator,
        lens="task",
    )
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for directive in resolved:
        directive_id = str(directive.get("id") or "")
        marker = directive_id or json.dumps(directive, sort_keys=True, default=str)
        if marker in seen:
            continue
        seen.add(marker)
        deduped.append(directive)
    return deduped


def _resolve_summary_directives(
    *,
    context: dict[str, Any],
    reporting_config: dict[str, Any],
) -> list[dict[str, Any]]:
    return _resolve_directives(
        context=context,
        reporting_config=reporting_config,
        iterator=_iter_summary_directives,
    )


def _resolve_judge_directives(
    *,
    context: dict[str, Any],
    reporting_config: dict[str, Any],
) -> list[dict[str, Any]]:
    return _resolve_directives(
        context=context,
        reporting_config=reporting_config,
        iterator=_iter_judge_directives,
    )


def _is_discrete_subject_label_facet(meta: dict[str, Any]) -> bool:
    facet_key = str(meta.get("facetKey") or "").strip()
    if not facet_key:
        # Fall back for callers that only set the unqualified key.
        facet_key = str(meta.get("key") or "").strip().rsplit(".", 1)[-1]
    if facet_key in DISCRETE_SUBJECT_LABEL_FACET_KEYS:
        return True
    return facet_key.endswith("_subject_label")


def _aggregate_field(
    *,
    meta: dict[str, Any],
    values: list[dict[str, Any]],
    artifact_ready_trials: int,
) -> dict[str, Any]:
    kind = str(meta.get("kind") or "").strip().lower()
    present_entries = [entry for entry in values if _has_value(entry.get("value"))]
    missing_count = max(artifact_ready_trials - len(present_entries), 0)
    # Catalog choice titles are discrete identities, not free-text themes.
    if _is_discrete_subject_label_facet(meta):
        kind = "categorical"
    else:
        # Survey choice ids are often emitted as textual strings; recover a real distribution.
        # Skip explanation/evidence roles — those are free-text even when short.
        role = str(meta.get("role") or "").strip().lower()
        if (
            kind == "textual"
            and role not in {"explanation", "evidence"}
            and _entries_look_categorical(present_entries)
        ):
            kind = "categorical"
    payload = {
        **meta,
        "kind": kind,
        "presentCount": len(present_entries),
        "missingCount": missing_count,
    }
    if kind == "numerical":
        payload["numerical"] = _aggregate_numerical(present_entries)
    elif kind == "categorical":
        payload["categorical"] = _aggregate_categorical(present_entries)
    else:
        payload["textual"] = _aggregate_textual(present_entries)
    return payload


def _entries_look_categorical(entries: list[dict[str, Any]]) -> bool:
    """True when values look like choice ids / enums, not free-text sentences."""
    if not entries:
        return False
    for entry in entries:
        raw = entry.get("value")
        if isinstance(raw, bool) or isinstance(raw, list):
            continue
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            return False
        text = str(raw or "").strip()
        if not text:
            continue
        if " " in text or "\n" in text or len(text) > 64:
            return False
        # Reject sentence fragments ("Affordable.") and Title Case words without
        # id separators; keep snake/kebab ids and short lowercase/UPPER tokens.
        if any(ch in text for ch in ".!?,;:"):
            return False
        if "_" not in text and "-" not in text:
            if not (text.islower() or text.isupper()):
                return False
    return True


AUTO_SUMMARY_SKIP_TEXT_LEAVES = frozenset({"task_goal_label"})


def _auto_summary_directives(
    *,
    meta: dict[str, Any],
    facets: list[dict[str, Any]],
    field_values: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Synthesize an LLM bucket-summary directive for each free-text reason facet.

    Persona explanations (outcome_reason, feedback_reason, process_notes, …) are
    best presented as a per-group LLM summary rather than raw quotes. These run
    through the same summary + LLM + cache pipeline as reporting.json directives,
    gated by the same reporting-LLM flag.
    """
    context_key = str(meta.get("key") or "")
    directives: list[dict[str, Any]] = []
    for facet in facets:
        if facet.get("kind") != "textual":
            continue
        if str(facet.get("role") or "") not in {"explanation", "evidence", "supporting_text"}:
            continue
        leaf = _facet_key_leaf(facet)
        if leaf in AUTO_SUMMARY_SKIP_TEXT_LEAVES:
            continue
        # Group only by the facet's explicitly declared target — never guessed.
        axis = _resolve_explained_axis(facet, facets, field_values)
        if axis is None:
            continue
        values = [
            str(entry.get("value") or "").strip()
            for entry in field_values.get(str(facet.get("key")), [])
            if _has_value(entry.get("value"))
        ]
        values = [value for value in values if value]
        unique = set(values)
        # Too few / low-diversity explanations aren't worth an LLM summary —
        # showing the handful of raw quotes is clearer (and matches the
        # cross-facet low-diversity skip).
        if len(values) < 3 or len(unique) < 3:
            continue
        directives.append(
            {
                "id": "{}.auto_summary.{}".format(context_key, leaf),
                "title": str(facet.get("label") or facet.get("facetKey") or leaf),
                "targetFacetKey": str(facet.get("facetKey") or leaf),
                "groupByFacetKey": str(axis.get("facetKey")) or None,
                "groupByMode": str(axis.get("mode")),
                "bands": axis.get("bands"),
                "summaryKind": "llm_bucket_summary",
                "instruction": (
                    "For each group, summarize the shared themes and notable differences across "
                    "these persona explanations in 1-2 sentences. Be faithful and concise; do not "
                    "invent facts."
                ),
                "auto": True,
            }
        )
    return directives


def _distribution_directive_dimensions(
    directive: dict[str, Any], stratify_fields: list[str]
) -> list[str]:
    """Persona dimensions for a distribution directive.

    Honors an explicit ``groupByPersonaDimensions`` list or single
    ``groupByPersonaDimension``; otherwise defaults to the cohort's
    ``sampling.fields`` so authors only need to name the facet.

    An explicit empty ``groupByPersonaDimensions: []`` (or
    ``"standalone": true``) means a cohort-level card with no persona cross —
    those render as independent facets in Persona insights (capped separately).
    """
    if directive.get("standalone") is True:
        return []
    if "groupByPersonaDimensions" in directive:
        raw = directive.get("groupByPersonaDimensions")
        if not isinstance(raw, list):
            return []
        return [str(item).strip() for item in raw if str(item).strip()]
    single = str(directive.get("groupByPersonaDimension") or "").strip()
    if single:
        return [single]
    return list(stratify_fields)


# Signal facets eligible for the interactive persona explorer: the hero result,
# numeric scores, and categorical evidence (never free-text or identities).
PERSONA_DISTRIBUTION_ROLES = frozenset({"primary", "score", "evidence"})
# Max cohort-level (non-crossed) cards per context in Persona insights.
PERSONA_STANDALONE_MAX = 2
# Categorical facets with more distinct values than this are treated as ids/labels.
PERSONA_DISTRIBUTION_MAX_CARDINALITY = 8
# Bookkeeping facets that carry no per-segment signal.
PERSONA_DISTRIBUTION_SKIP_LEAVES = frozenset(
    {"task_author", "verifier_mode", "task_goal_label"}
)


def _persona_dimension_keys(persona_dimensions: dict[str, dict[str, Any]]) -> list[str]:
    """Ordered union of every persona dimension key present in the cohort."""
    keys: list[str] = []
    seen: set[str] = set()
    for dims in persona_dimensions.values():
        if not isinstance(dims, dict):
            continue
        for key in dims:
            normalized = str(key).strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                keys.append(normalized)
    return keys


def _is_persona_explorer_facet(facet: dict[str, Any]) -> bool:
    """Whether a facet is worth offering in the interactive persona explorer.

    Keeps numeric/categorical signals (primary/score/evidence); drops free-text,
    identities, near-unique categoricals, and bookkeeping leaves so the picker
    stays meaningful instead of exhaustive.
    """
    kind = str(facet.get("kind") or "").strip().lower()
    role = str(facet.get("role") or "").strip().lower()
    if kind not in {"numerical", "categorical"} or role not in PERSONA_DISTRIBUTION_ROLES:
        return False
    if _is_discrete_subject_label_facet(facet):
        return False
    leaf = _facet_key_leaf(facet)
    if leaf in PERSONA_DISTRIBUTION_SKIP_LEAVES:
        return False
    if leaf.endswith(("_subject_id", "_subject_label", "_id", "_label")):
        return False
    return True


def _build_persona_distribution(
    *,
    context_key: str,
    facet: dict[str, Any],
    field_values: dict[str, list[dict[str, Any]]],
    dimension: str,
    persona_dimensions: dict[str, dict[str, Any]],
    directive_id: str | None = None,
    label: str | None = None,
) -> dict[str, Any] | None:
    """Cross-tab one signal facet against one persona dimension.

    Returns a distribution object (counts + per-segment stats) or ``None`` when
    the pairing has fewer than two non-empty segments. Shared by the declared
    defaults and the interactive explorer options so both render identically.
    """
    kind = str(facet.get("kind") or "").strip().lower()
    if kind not in {"numerical", "categorical"}:
        return None
    entries = [
        entry
        for entry in field_values.get(str(facet.get("key")), [])
        if _has_value(entry.get("value")) and entry.get("trialName") is not None
    ]
    if len(entries) < 2:
        return None
    bucket_map = _persona_attribute_bucket_map(entries, dimension, persona_dimensions)
    nonempty = {
        bucket: bucket_entries
        for bucket, bucket_entries in bucket_map.items()
        if bucket_entries
    }
    if len(nonempty) < 2:
        return None
    leaf = _facet_key_leaf(facet)
    buckets: list[dict[str, Any]] = []
    for bucket, bucket_entries in sorted(
        nonempty.items(), key=lambda item: (-len(item[1]), item[0])
    ):
        record: dict[str, Any] = {"bucket": bucket, "count": len(bucket_entries)}
        if kind == "numerical":
            record["numerical"] = _aggregate_numerical(bucket_entries)
        else:
            record["categorical"] = _aggregate_categorical(bucket_entries)
        buckets.append(record)
    distribution: dict[str, Any] = {
        "id": directive_id
        or "{}.persona_dist.{}.{}".format(context_key, leaf, dimension),
        "facetKey": str(facet.get("facetKey") or leaf),
        "facetLabel": str(label or facet.get("label") or leaf),
        "kind": kind,
        "groupByPersonaDimension": dimension,
        "groupByLabel": _humanize_persona_dimension(dimension),
        "lens": "persona",
        "total": sum(len(items) for items in nonempty.values()),
        "buckets": buckets,
    }
    if kind == "categorical":
        overall_categories = [
            row["value"] for row in _aggregate_categorical(entries).get("counts", [])
        ]
        if overall_categories:
            distribution["categories"] = overall_categories
    return distribution


def _config_persona_distributions(
    *,
    meta: dict[str, Any],
    facets: list[dict[str, Any]],
    field_values: dict[str, list[dict[str, Any]]],
    persona_dimensions: dict[str, dict[str, Any]],
    stratify_fields: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Default persona cards from ``reporting.json`` distributions.

    Returns ``(cross_tabs, standalone_facets)``:
    - cross-tabs: signal × persona dimension heatmaps (Persona insights)
    - standalone: up to ``PERSONA_STANDALONE_MAX`` cohort-level single facets
      (explicit ``groupByPersonaDimensions: []`` or ``standalone: true``)
    """
    directives = meta.get("distributions")
    if not isinstance(directives, list) or not directives:
        return [], []
    context_key = str(meta.get("key") or "")
    facet_by_leaf = {_facet_key_leaf(facet): facet for facet in facets}
    distributions: list[dict[str, Any]] = []
    standalones: list[dict[str, Any]] = []
    seen_cross: set[str] = set()
    seen_standalone: set[str] = set()
    for directive in directives:
        if not isinstance(directive, dict):
            continue
        facet_key = str(directive.get("facetKey") or "").strip()
        if not facet_key:
            continue
        facet = facet_by_leaf.get(facet_key.split(".")[-1].replace("-", "_"))
        if facet is None:
            continue
        leaf = _facet_key_leaf(facet)
        dimensions = _distribution_directive_dimensions(directive, stratify_fields)
        directive_id = str(directive.get("id") or "").strip()
        title = str(directive.get("title") or "").strip()
        if not dimensions:
            if leaf in seen_standalone or len(standalones) >= PERSONA_STANDALONE_MAX:
                continue
            # Standalone cards do not need persona dimension data.
            entry = {
                **facet,
                "label": title or str(facet.get("label") or leaf),
            }
            if directive_id:
                entry["standaloneId"] = directive_id
            standalones.append(entry)
            seen_standalone.add(leaf)
            continue
        if not persona_dimensions:
            continue
        for dimension in dimensions:
            marker = "{}|{}".format(leaf, dimension)
            if marker in seen_cross:
                continue
            distribution = _build_persona_distribution(
                context_key=context_key,
                facet=facet,
                field_values=field_values,
                dimension=dimension,
                persona_dimensions=persona_dimensions,
                directive_id=directive_id if directive_id and len(dimensions) == 1 else None,
                label=title or None,
            )
            if distribution is None:
                continue
            seen_cross.add(marker)
            distributions.append(distribution)
    return distributions, standalones


def _persona_distribution_options(
    *,
    meta: dict[str, Any],
    facets: list[dict[str, Any]],
    field_values: dict[str, list[dict[str, Any]]],
    persona_dimensions: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Every eligible ``(signal facet × persona dimension)`` cross-tab.

    Backs the interactive explorer (facet on the left, persona dimension on the
    right). Bounded by facets × dimensions and independent of cohort size, so it
    stays cheap even for large runs. This is *not* rendered by default — it only
    populates the picker; the default cards come from
    :func:`_config_persona_distributions`.
    """
    if not persona_dimensions:
        return []
    context_key = str(meta.get("key") or "")
    dimension_keys = _persona_dimension_keys(persona_dimensions)
    if not dimension_keys:
        return []
    options: list[dict[str, Any]] = []
    for facet in facets:
        if not _is_persona_explorer_facet(facet):
            continue
        kind = str(facet.get("kind") or "").strip().lower()
        if kind == "categorical":
            entries = [
                entry
                for entry in field_values.get(str(facet.get("key")), [])
                if _has_value(entry.get("value")) and entry.get("trialName") is not None
            ]
            distinct = {_categorical_key(entry.get("value")) for entry in entries}
            if len(distinct) > PERSONA_DISTRIBUTION_MAX_CARDINALITY:
                continue
        for dimension in dimension_keys:
            distribution = _build_persona_distribution(
                context_key=context_key,
                facet=facet,
                field_values=field_values,
                dimension=dimension,
                persona_dimensions=persona_dimensions,
            )
            if distribution is not None:
                options.append(distribution)
    return options


def _aggregate_context(
    *,
    meta: dict[str, Any],
    facet_keys: list[str],
    fields_by_key: dict[str, dict[str, Any]],
    field_values: dict[str, list[dict[str, Any]]],
    persona_dimensions: dict[str, dict[str, Any]] | None = None,
    stratify_fields: list[str] | None = None,
) -> dict[str, Any]:
    persona_dimensions = persona_dimensions or {}
    facets = [fields_by_key[key] for key in facet_keys if key in fields_by_key]
    payload = {
        **meta,
        "facets": facets,
    }
    existing_directives = (
        meta.get("summaryAnalyses") if isinstance(meta.get("summaryAnalyses"), list) else []
    )
    # (targetFacetKey, groupByFacetKey) pairs a task already declared explicitly.
    existing_pairs = {
        (
            str(directive.get("targetFacetKey")),
            str(directive.get("groupByFacetKey") or ""),
        )
        for directive in existing_directives
        if isinstance(directive, dict)
    }
    # Schema-bound directives are additive: they add the reason's declared axis
    # (e.g. reason by rating) without suppressing an explicit reporting.json view
    # of the same reason on a different axis. Skip only exact-pair duplicates.
    auto_directives = [
        directive
        for directive in _auto_summary_directives(
            meta=meta, facets=facets, field_values=field_values
        )
        if (
            str(directive.get("targetFacetKey")),
            str(directive.get("groupByFacetKey") or ""),
        )
        not in existing_pairs
    ]
    summary_meta = (
        {**meta, "summaryAnalyses": [*existing_directives, *auto_directives]}
        if auto_directives
        else meta
    )
    summaries = _aggregate_context_summaries(
        meta=summary_meta,
        facets=facets,
        field_values=field_values,
        persona_dimensions=persona_dimensions,
    )
    if summaries:
        payload["summaries"] = summaries
    judges = _aggregate_context_judges(
        meta=meta,
        facets=facets,
        field_values=field_values,
        persona_dimensions=persona_dimensions,
    )
    if judges:
        payload["judges"] = judges
    # Keep the raw-quote cross-facet views too: the frontend shows the LLM
    # summary when it completed, and falls back to these example quotes otherwise.
    cross_facet_views = _aggregate_context_cross_facet_views(
        facets=facets,
        field_values=field_values,
    )
    if cross_facet_views:
        payload["crossFacetViews"] = cross_facet_views
    # Persona-insight lens: author-declared distributions from reporting.json.
    # Cross-tabs (signal × persona dim) + up to 2 standalone cohort facets.
    persona_distributions, persona_standalones = _config_persona_distributions(
        meta=meta,
        facets=facets,
        field_values=field_values,
        persona_dimensions=persona_dimensions,
        stratify_fields=stratify_fields or [],
    )
    if persona_distributions:
        payload["personaDistributions"] = persona_distributions
    if persona_standalones:
        payload["personaStandaloneFacets"] = persona_standalones
    # Interactive explorer: every eligible facet × dimension pairing (bounded,
    # non-LLM), shown only behind the picker — not as default cards.
    persona_distribution_options = _persona_distribution_options(
        meta=meta,
        facets=facets,
        field_values=field_values,
        persona_dimensions=persona_dimensions,
    )
    if persona_distribution_options:
        payload["personaDistributionOptions"] = persona_distribution_options
    return payload


def _apply_llm_reporting(
    *,
    payload: dict[str, Any],
    previous_payload: dict[str, Any] | None,
    llm_client: Any | None,
    enable_llm: bool | None,
) -> dict[str, Any]:
    previous_index = _index_previous_llm_units(previous_payload)
    llm_enabled = _reporting_llm_enabled(enable_llm)
    client = _reporting_llm_client(llm_client) if llm_enabled else None
    client_error = None
    if llm_enabled and client is None:
        client_error = "Reporting LLM client unavailable for configured model."
    for context in payload.get("contexts", []) if isinstance(payload.get("contexts"), list) else []:
        if not isinstance(context, dict):
            continue
        context_key = str(context.get("key") or "")
        summaries = context.get("summaries")
        if isinstance(summaries, list):
            for summary in summaries:
                if not isinstance(summary, dict):
                    continue
                fingerprint = _fingerprint_reporting_unit(summary)
                summary["llmFingerprint"] = fingerprint
                cached = previous_index.get(("summary", context_key, str(summary.get("id") or "")))
                if _cached_result_matches(cached, fingerprint):
                    _reuse_cached_summary(summary, cached)
                    continue
                if client is not None and str(summary.get("status") or "").startswith("ready_for_llm"):
                    _execute_summary_llm(summary, client=client)
                elif client_error and str(summary.get("status") or "").startswith("ready_for_llm"):
                    summary["status"] = "llm_failed"
                    summary["error"] = client_error
        judges = context.get("judges")
        if isinstance(judges, list):
            for judge in judges:
                if not isinstance(judge, dict):
                    continue
                fingerprint = _fingerprint_reporting_unit(judge)
                judge["llmFingerprint"] = fingerprint
                cached = previous_index.get(("judge", context_key, str(judge.get("id") or "")))
                if _cached_result_matches(cached, fingerprint):
                    _reuse_cached_judge(judge, cached)
                    continue
                if client is not None and str(judge.get("status") or "").startswith("ready_for_llm"):
                    _execute_judge_llm(judge, client=client)
                elif client_error and str(judge.get("status") or "").startswith("ready_for_llm"):
                    judge["status"] = "llm_failed"
                    judge["error"] = client_error
    return payload


def _index_previous_llm_units(previous_payload: dict[str, Any] | None) -> dict[tuple[str, str, str], dict[str, Any]]:
    index: dict[tuple[str, str, str], dict[str, Any]] = {}
    if not isinstance(previous_payload, dict):
        return index
    contexts = previous_payload.get("contexts")
    if not isinstance(contexts, list):
        return index
    for context in contexts:
        if not isinstance(context, dict):
            continue
        context_key = str(context.get("key") or "")
        for kind in ("summaries", "judges"):
            units = context.get(kind)
            if not isinstance(units, list):
                continue
            for unit in units:
                if not isinstance(unit, dict):
                    continue
                label = "summary" if kind == "summaries" else "judge"
                index[(label, context_key, str(unit.get("id") or ""))] = unit
    return index


def _cached_result_matches(cached: dict[str, Any] | None, fingerprint: str) -> bool:
    if not isinstance(cached, dict):
        return False
    if str(cached.get("llmFingerprint") or "") != fingerprint:
        return False
    # Only reuse successes — llm_failed must be retryable on the next reporting pass.
    return str(cached.get("status") or "") == "llm_completed"


def _reuse_cached_summary(current: dict[str, Any], cached: dict[str, Any]) -> None:
    current["status"] = cached.get("status")
    current["error"] = cached.get("error")
    current["overall"] = cached.get("overall")
    cached_buckets = {
        str(bucket.get("bucket") or ""): bucket
        for bucket in cached.get("buckets", [])
        if isinstance(bucket, dict)
    }
    for bucket in current.get("buckets", []) if isinstance(current.get("buckets"), list) else []:
        cached_bucket = cached_buckets.get(str(bucket.get("bucket") or ""))
        if not cached_bucket:
            continue
        bucket["summary"] = cached_bucket.get("summary")
        bucket["summaryType"] = cached_bucket.get("summaryType")


def _reuse_cached_judge(current: dict[str, Any], cached: dict[str, Any]) -> None:
    current["status"] = cached.get("status")
    current["error"] = cached.get("error")
    current["overall"] = cached.get("overall")
    current["overallAssessment"] = cached.get("overallAssessment")
    current["signalStats"] = cached.get("signalStats")
    current["total"] = cached.get("total")
    cached_buckets = {
        str(bucket.get("bucket") or ""): bucket
        for bucket in cached.get("buckets", [])
        if isinstance(bucket, dict)
    }
    for bucket in current.get("buckets", []) if isinstance(current.get("buckets"), list) else []:
        cached_bucket = cached_buckets.get(str(bucket.get("bucket") or ""))
        if not cached_bucket:
            continue
        bucket["assessment"] = cached_bucket.get("assessment")
        bucket["signals"] = cached_bucket.get("signals")
        bucket["signalStats"] = cached_bucket.get("signalStats")


def _build_reporting_view(payload: dict[str, Any]) -> dict[str, Any]:
    llm_units = list(_iter_llm_reporting_units(payload))
    status_counts = Counter(
        str(unit.get("status") or "unknown")
        for _, unit in llm_units
    )
    total_units = len(llm_units)
    summary_units = sum(1 for kind, _ in llm_units if kind == "summary")
    judge_units = sum(1 for kind, _ in llm_units if kind == "judge")
    ready_units = status_counts.get("ready_for_llm", 0)
    completed_units = status_counts.get("llm_completed", 0)
    failed_units = status_counts.get("llm_failed", 0)
    return {
        "status": _reporting_overall_status(
            total_units=total_units,
            ready_units=ready_units,
            completed_units=completed_units,
            failed_units=failed_units,
        ),
        "llmEnabled": _reporting_llm_enabled(None),
        "model": (
            os.environ.get(REPORTING_LLM_MODEL_ENV)
            or DEFAULT_REPORTING_LLM_MODEL
        ).strip()
        or DEFAULT_REPORTING_LLM_MODEL,
        "totalUnits": total_units,
        "summaryUnits": summary_units,
        "judgeUnits": judge_units,
        "readyUnits": ready_units,
        "completedUnits": completed_units,
        "failedUnits": failed_units,
        "updatedAt": payload.get("generatedAt"),
    }


def _iter_llm_reporting_units(payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    contexts = payload.get("contexts")
    if not isinstance(contexts, list):
        return []
    units: list[tuple[str, dict[str, Any]]] = []
    for context in contexts:
        if not isinstance(context, dict):
            continue
        summaries = context.get("summaries")
        if isinstance(summaries, list):
            for summary in summaries:
                if not isinstance(summary, dict):
                    continue
                kind = str(summary.get("summaryKind") or "").strip().lower()
                status = str(summary.get("status") or "").strip().lower()
                if kind.startswith("llm_") or status.startswith("ready_for_llm") or status.startswith("llm_"):
                    units.append(("summary", summary))
        judges = context.get("judges")
        if isinstance(judges, list):
            for judge in judges:
                if not isinstance(judge, dict):
                    continue
                kind = str(judge.get("judgeKind") or "").strip().lower()
                status = str(judge.get("status") or "").strip().lower()
                if kind.startswith("llm_") or status.startswith("ready_for_llm") or status.startswith("llm_"):
                    units.append(("judge", judge))
    return units


def _reporting_overall_status(
    *,
    total_units: int,
    ready_units: int,
    completed_units: int,
    failed_units: int,
) -> str:
    if total_units <= 0:
        return "not_applicable"
    if completed_units == total_units:
        return "completed"
    if failed_units == total_units:
        return "failed"
    if ready_units == total_units:
        return "ready"
    if completed_units > 0 and failed_units > 0 and ready_units > 0:
        return "partial_with_errors"
    if completed_units > 0 and failed_units > 0:
        return "completed_with_errors"
    if completed_units > 0 and ready_units > 0:
        return "partial"
    if failed_units > 0 and ready_units > 0:
        return "failed"
    return "ready"


def _reporting_llm_enabled(enable_llm: bool | None) -> bool:
    if enable_llm is not None:
        return enable_llm
    raw = os.environ.get(REPORTING_LLM_ENABLE_ENV, "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _reporting_llm_client(client: Any | None) -> Any | None:
    if client is not None:
        return client
    model = (
        os.environ.get(REPORTING_LLM_MODEL_ENV)
        or DEFAULT_REPORTING_LLM_MODEL
    ).strip() or DEFAULT_REPORTING_LLM_MODEL
    provider, bare_model = _normalize_reporting_model(model)
    if provider != "openai":
        return None
    from playground.openai_client import OpenAIChatClient

    return OpenAIChatClient(model=bare_model, temperature=0.2)


def _normalize_reporting_model(model: str) -> tuple[str, str]:
    normalized = model.strip()
    if "/" in normalized:
        provider, bare = normalized.split("/", 1)
        return provider, bare
    return "openai", normalized


def _fingerprint_reporting_unit(unit: dict[str, Any]) -> str:
    payload = {
        "id": unit.get("id"),
        "title": unit.get("title"),
        "targetFacetKey": unit.get("targetFacetKey"),
        "groupByFacetKey": unit.get("groupByFacetKey"),
        "groupByMode": unit.get("groupByMode"),
        "summaryKind": unit.get("summaryKind"),
        "judgeKind": unit.get("judgeKind"),
        "instruction": unit.get("instruction"),
        "prompt": unit.get("prompt"),
        "rubric": unit.get("rubric"),
        "signals": unit.get("signals"),
        "buckets": unit.get("buckets"),
        "scanSamples": unit.get("scanSamples"),
        "overall": unit.get("overall"),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _lean_summary_buckets_for_llm(buckets: list[Any]) -> list[dict[str, Any]]:
    """Shrink bucket payloads so large cohort prompts stay within model limits."""
    lean: list[dict[str, Any]] = []
    for bucket in buckets:
        if not isinstance(bucket, dict):
            continue
        samples_raw = bucket.get("samples")
        samples: list[str] = []
        if isinstance(samples_raw, list):
            for sample in samples_raw[:SUMMARY_LLM_SAMPLE_LIMIT]:
                text = str(sample or "").strip()
                if not text:
                    continue
                samples.append(text[:SUMMARY_LLM_SAMPLE_CHARS])
        lean.append(
            {
                "bucket": bucket.get("bucket"),
                "count": bucket.get("count"),
                "samples": samples,
            }
        )
    return lean


def _summary_llm_system_prompt() -> str:
    return (
        "You are an evaluation reporting assistant. Summarize grouped user text samples "
        "concisely and return strict JSON."
    )


def _summary_llm_user_payload(
    *,
    title: Any,
    instruction: str,
    buckets: list[dict[str, Any]],
) -> str:
    return json.dumps(
        {
            "task": "Summarize grouped text buckets for a completed evaluation job.",
            "title": title,
            "instruction": instruction
            or "Summarize each bucket faithfully without inventing new facts.",
            "buckets": buckets,
            "expectedOutput": {
                "overallSummary": "string",
                "bucketSummaries": [{"bucket": "string", "summary": "string"}],
            },
        },
        ensure_ascii=False,
        indent=2,
    )


def _bucket_summaries_from_llm_result(result: dict[str, Any]) -> dict[str, str]:
    return {
        str(item.get("bucket") or ""): str(item.get("summary") or "").strip()
        for item in result.get("bucketSummaries", [])
        if isinstance(item, dict) and str(item.get("bucket") or "").strip()
    }


def _apply_bucket_summaries(
    summary: dict[str, Any],
    bucket_summaries: dict[str, str],
) -> int:
    applied = 0
    for bucket in summary.get("buckets", []) if isinstance(summary.get("buckets"), list) else []:
        if not isinstance(bucket, dict):
            continue
        value = bucket_summaries.get(str(bucket.get("bucket") or ""))
        if not value:
            continue
        bucket["summary"] = value
        bucket["summaryType"] = "llm"
        applied += 1
    return applied


def _set_summary_overall(summary: dict[str, Any], overall_summary: str) -> None:
    text = overall_summary.strip()
    if not text:
        return
    overall = summary.get("overall")
    if not isinstance(overall, dict):
        overall = {}
        summary["overall"] = overall
    overall["summary"] = text
    overall["summaryType"] = "llm"


def _merge_summary_chunk_overalls(
    *,
    client: Any,
    title: Any,
    chunk_overalls: list[str],
) -> str:
    if not chunk_overalls:
        return ""
    if len(chunk_overalls) == 1:
        return chunk_overalls[0]
    try:
        result = client.complete_json(
            "You are an evaluation reporting assistant. Merge partial summaries into one "
            "concise overall summary. Return strict JSON.",
            json.dumps(
                {
                    "task": "Merge chunk summaries into one overallSummary.",
                    "title": title,
                    "partialSummaries": chunk_overalls,
                    "expectedOutput": {"overallSummary": "string"},
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
    except Exception:  # noqa: BLE001
        return " ".join(chunk_overalls)
    if not isinstance(result, dict):
        return " ".join(chunk_overalls)
    merged = str(result.get("overallSummary") or "").strip()
    return merged or " ".join(chunk_overalls)


def _execute_summary_llm(summary: dict[str, Any], *, client: Any) -> None:
    buckets = summary.get("buckets")
    if not isinstance(buckets, list) or not buckets:
        summary["status"] = "llm_failed"
        summary["error"] = "no buckets to summarize"
        return

    instruction = str(summary.get("instruction") or "").strip()
    title = summary.get("title")
    system = _summary_llm_system_prompt()

    # Small jobs keep the single-shot path; large cohort group-bys are chunked so
    # the model can return strict JSON without truncating mid-object.
    if len(buckets) <= SUMMARY_LLM_BUCKET_CHUNK:
        user = _summary_llm_user_payload(
            title=title,
            instruction=instruction,
            buckets=_lean_summary_buckets_for_llm(buckets),
        )
        try:
            result = client.complete_json(system, user)
        except Exception as exc:  # noqa: BLE001
            summary["status"] = "llm_failed"
            summary["error"] = str(exc)
            return
        if not isinstance(result, dict):
            summary["status"] = "llm_failed"
            summary["error"] = "Reporting LLM returned a non-object JSON payload."
            return
        _set_summary_overall(summary, str(result.get("overallSummary") or ""))
        _apply_bucket_summaries(summary, _bucket_summaries_from_llm_result(result))
        summary["status"] = "llm_completed"
        summary.pop("error", None)
        return

    bucket_summaries: dict[str, str] = {}
    chunk_overalls: list[str] = []
    chunk_errors: list[str] = []
    total_chunks = (len(buckets) + SUMMARY_LLM_BUCKET_CHUNK - 1) // SUMMARY_LLM_BUCKET_CHUNK
    for chunk_index, start in enumerate(range(0, len(buckets), SUMMARY_LLM_BUCKET_CHUNK), start=1):
        chunk = buckets[start : start + SUMMARY_LLM_BUCKET_CHUNK]
        user = _summary_llm_user_payload(
            title=title,
            instruction=instruction,
            buckets=_lean_summary_buckets_for_llm(chunk),
        )
        try:
            result = client.complete_json(system, user)
        except Exception as exc:  # noqa: BLE001
            chunk_errors.append("chunk {}/{}: {}".format(chunk_index, total_chunks, exc))
            continue
        if not isinstance(result, dict):
            chunk_errors.append(
                "chunk {}/{}: Reporting LLM returned a non-object JSON payload.".format(
                    chunk_index, total_chunks
                )
            )
            continue
        overall = str(result.get("overallSummary") or "").strip()
        if overall:
            chunk_overalls.append(overall)
        bucket_summaries.update(_bucket_summaries_from_llm_result(result))

    applied = _apply_bucket_summaries(summary, bucket_summaries)
    if chunk_overalls:
        _set_summary_overall(
            summary,
            _merge_summary_chunk_overalls(
                client=client,
                title=title,
                chunk_overalls=chunk_overalls,
            ),
        )

    if chunk_errors and applied == 0:
        summary["status"] = "llm_failed"
        summary["error"] = "; ".join(chunk_errors[:3])
        return
    if chunk_errors:
        summary["status"] = "llm_failed"
        summary["error"] = "{}; applied {}/{} bucket summaries".format(
            "; ".join(chunk_errors[:3]),
            applied,
            len(buckets),
        )
        return

    summary["status"] = "llm_completed"
    summary.pop("error", None)


def _execute_judge_llm(judge: dict[str, Any], *, client: Any) -> None:
    signals = judge.get("signals") if isinstance(judge.get("signals"), list) else []
    samples = judge.get("scanSamples") if isinstance(judge.get("scanSamples"), list) else []
    if not signals or not samples:
        judge["status"] = "llm_failed"
        judge["error"] = "no samples or signals to scan"
        return

    system = (
        "You are an evaluation judge. Score EACH sample independently against the provided "
        "signals: for every sample, list which signal keys its own words clearly describe or "
        "strongly imply. Do not infer beyond the text. Return strict JSON."
    )
    user = json.dumps(
        {
            "task": "Independently score each sample against the signals.",
            "title": judge.get("title"),
            "prompt": judge.get("prompt"),
            "rubric": judge.get("rubric"),
            "signals": [
                {"key": s.get("key"), "label": s.get("label")}
                for s in signals
                if isinstance(s, dict)
            ],
            "samples": [
                {"id": s.get("id"), "text": s.get("text")}
                for s in samples
                if isinstance(s, dict)
            ],
            "expectedOutput": {
                "overallAssessment": "one short sentence summarizing the dominant signals",
                "samples": [{"id": 0, "present": ["signalKey"]}],
            },
        },
        ensure_ascii=False,
        indent=2,
    )
    try:
        result = client.complete_json(system, user)
    except Exception as exc:  # noqa: BLE001
        judge["status"] = "llm_failed"
        judge["error"] = str(exc)
        return

    valid_keys = {str(s.get("key")) for s in signals if isinstance(s, dict) and s.get("key")}
    present_by_id: dict[int, set[str]] = {}
    raw_samples = result.get("samples")
    for item in raw_samples if isinstance(raw_samples, list) else []:
        if not isinstance(item, dict):
            continue
        try:
            sid = int(item.get("id"))
        except (TypeError, ValueError):
            continue
        keys = item.get("present")
        if isinstance(keys, list):
            present_by_id[sid] = {
                str(k).strip() for k in keys if str(k).strip() in valid_keys
            }

    total = len(samples)
    group_totals: dict[str, int] = {}
    group_present: dict[str, dict[str, int]] = {}
    for sample in samples:
        grp = str(sample.get("group") or "All")
        group_totals[grp] = group_totals.get(grp, 0) + 1

    signal_stats: list[dict[str, Any]] = []
    for signal in signals:
        if not isinstance(signal, dict):
            continue
        key = str(signal.get("key") or "").strip()
        if not key:
            continue
        present_count = 0
        examples: list[str] = []
        for sample in samples:
            try:
                sid = int(sample.get("id"))
            except (TypeError, ValueError):
                continue
            if key not in present_by_id.get(sid, set()):
                continue
            present_count += 1
            grp = str(sample.get("group") or "All")
            group_bucket = group_present.setdefault(grp, {})
            group_bucket[key] = group_bucket.get(key, 0) + 1
            text = str(sample.get("text") or "").strip()
            if text and len(examples) < 3:
                examples.append(text)
        signal_stats.append(
            {
                "key": key,
                "label": signal.get("label") or key,
                "present": present_count,
                "total": total,
                "examples": examples,
            }
        )

    judge["signalStats"] = signal_stats
    judge["total"] = total
    for bucket in judge.get("buckets", []) if isinstance(judge.get("buckets"), list) else []:
        grp = str(bucket.get("bucket") or "")
        present_map = group_present.get(grp, {})
        group_total = group_totals.get(grp, bucket.get("count") or 0)
        bucket["signalStats"] = [
            {
                "key": str(s.get("key")),
                "label": s.get("label") or s.get("key"),
                "present": present_map.get(str(s.get("key")), 0),
                "total": group_total,
            }
            for s in signals
            if isinstance(s, dict) and s.get("key")
        ]

    overall_assessment = str(result.get("overallAssessment") or "").strip()
    if overall_assessment:
        judge["overallAssessment"] = overall_assessment
    judge["status"] = "llm_completed"
    judge.pop("error", None)


def _directive_lens(directive: dict[str, Any], *, group_by_mode: str) -> str:
    """Which analysis tab a reporting unit belongs to.

    - "general": Layer-1 auto reason summaries (common analysis)
    - "task":    Custom analysis (SUT/task-owner lens; the default)

    Summaries and signal scans always live in Custom analysis, even when grouped
    by a persona dimension (that is just an optional grouping axis). The dedicated
    persona lens is served by distributions (facts), not by LLM analyses.
    """
    explicit = str(directive.get("lens") or "").strip().lower()
    if explicit in {"task", "persona", "general"}:
        return explicit
    # Auto reason summaries with no explicit lens are Layer-1 common analysis.
    if directive.get("auto"):
        return "general"
    return "task"


def _humanize_persona_dimension(dimension: str) -> str:
    key = str(dimension or "").strip().lower()
    labels = {
        "trust_level": "Trust level",
        "age_bracket": "Age",
        "age": "Age",
        "cog_skepticism": "Skepticism",
    }
    if key in labels:
        return labels[key]
    cleaned = key.replace("_", " ").strip()
    return cleaned[:1].upper() + cleaned[1:] if cleaned else str(dimension)


def _persona_attribute_bucket_map(
    target_entries: list[dict[str, Any]],
    dimension: str,
    persona_dimensions: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Bucket target entries by a persona profile dimension (customer-insight lens)."""
    bucket_map: dict[str, list[dict[str, Any]]] = {}
    for entry in target_entries:
        persona_id = entry.get("personaId")
        dims = persona_dimensions.get(str(persona_id)) if persona_id is not None else None
        if not isinstance(dims, dict):
            continue
        value = dims.get(dimension)
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        bucket_map.setdefault(str(value), []).append(entry)
    return bucket_map


def _aggregate_context_summaries(
    *,
    meta: dict[str, Any],
    facets: list[dict[str, Any]],
    field_values: dict[str, list[dict[str, Any]]],
    persona_dimensions: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    facet_lookup = {str(facet.get("facetKey") or facet.get("key")): facet for facet in facets}
    directives = meta.get("summaryAnalyses")
    if not isinstance(directives, list):
        return []
    summaries: list[dict[str, Any]] = []
    for index, directive in enumerate(directives):
        summary = _aggregate_summary_directive(
            directive=directive,
            index=index,
            context_key=str(meta.get("key") or ""),
            facet_lookup=facet_lookup,
            field_values=field_values,
            persona_dimensions=persona_dimensions or {},
        )
        if summary:
            summaries.append(summary)
    return summaries


def _aggregate_summary_directive(
    *,
    directive: dict[str, Any],
    index: int,
    context_key: str,
    facet_lookup: dict[str, dict[str, Any]],
    field_values: dict[str, list[dict[str, Any]]],
    persona_dimensions: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    persona_dimensions = persona_dimensions or {}
    target_facet_key = str(directive.get("targetFacetKey") or "").strip()
    if not target_facet_key:
        return None
    target_field = facet_lookup.get(target_facet_key)
    if target_field is None or target_field.get("kind") != "textual":
        return None
    group_by_mode = str(directive.get("groupByMode") or "none").strip().lower()
    if group_by_mode not in SUMMARY_GROUP_BY_MODES:
        group_by_mode = "none"
    group_by_facet_key = str(directive.get("groupByFacetKey") or "").strip() or None
    group_by_field = facet_lookup.get(group_by_facet_key) if group_by_facet_key else None
    persona_dimension = str(directive.get("groupByPersonaDimension") or "").strip() or None
    target_entries = [
        entry
        for entry in field_values.get(str(target_field.get("key")), [])
        if _has_value(entry.get("value")) and entry.get("trialName") is not None
    ]
    if not target_entries:
        return None

    bucket_map: dict[str, list[dict[str, Any]]] = {}
    if group_by_mode == "persona_attribute":
        if not persona_dimension:
            return None
        bucket_map = _persona_attribute_bucket_map(
            target_entries, persona_dimension, persona_dimensions
        )
        if not bucket_map:
            return None
    elif group_by_mode == "none" or group_by_field is None:
        bucket_map["All"] = target_entries
    elif group_by_mode == "categorical":
        group_entries = {
            str(entry.get("trialName")): _categorical_key(entry.get("value"))
            for entry in field_values.get(str(group_by_field.get("key")), [])
            if entry.get("trialName") is not None and _has_value(entry.get("value"))
        }
        for entry in target_entries:
            trial_name = str(entry.get("trialName"))
            bucket = group_entries.get(trial_name)
            if bucket is None:
                continue
            bucket_map.setdefault(bucket, []).append(entry)
    else:
        bands = _normalize_numeric_bands(directive.get("bands"))
        if not bands:
            # No explicit bands: auto-bin the numeric axis by its distribution.
            bands = _auto_numeric_bands(
                _numeric_axis_values(group_by_field, field_values)
            )
        if not bands:
            return None
        group_entries = {
            str(entry.get("trialName")): entry.get("value")
            for entry in field_values.get(str(group_by_field.get("key")), [])
            if entry.get("trialName") is not None and _has_value(entry.get("value"))
        }
        for entry in target_entries:
            trial_name = str(entry.get("trialName"))
            bucket = _match_numeric_band(group_entries.get(trial_name), bands)
            if bucket is None:
                continue
            bucket_map.setdefault(bucket, []).append(entry)

    overall = _aggregate_textual(target_entries)
    buckets = [
        {
            "bucket": bucket,
            "count": len(entries),
            "samples": overall_bucket.get("samples"),
            "summary": overall_bucket.get("summary"),
            "summaryType": overall_bucket.get("summaryType"),
        }
        for bucket, entries in sorted(
            bucket_map.items(),
            key=lambda item: (-len(item[1]), item[0]),
        )
        for overall_bucket in [_aggregate_textual(entries)]
    ]
    if not buckets:
        return None
    target_label = str(target_field.get("label") or target_facet_key)
    if group_by_mode == "persona_attribute" and persona_dimension:
        group_by_label = _humanize_persona_dimension(persona_dimension)
    else:
        group_by_label = str(
            (group_by_field.get("label") if isinstance(group_by_field, dict) else None)
            or group_by_facet_key
            or "All"
        )
    summary_kind = str(directive.get("summaryKind") or "bucketed_text").strip()
    return {
        "id": str(directive.get("id") or "{}.summary_{}".format(context_key, index + 1)),
        "title": str(directive.get("title") or "{} by {}".format(target_label, group_by_label)),
        "targetFacetKey": target_facet_key,
        "groupByFacetKey": group_by_facet_key,
        "groupByPersonaDimension": persona_dimension,
        "groupByLabel": group_by_label,
        "groupByMode": group_by_mode,
        "lens": _directive_lens(directive, group_by_mode=group_by_mode),
        "summaryKind": summary_kind,
        "instruction": directive.get("instruction"),
        "auto": bool(directive.get("auto")),
        "status": "ready_for_llm" if summary_kind.startswith("llm_") else "heuristic",
        "overall": overall,
        "buckets": buckets,
    }


def _aggregate_context_judges(
    *,
    meta: dict[str, Any],
    facets: list[dict[str, Any]],
    field_values: dict[str, list[dict[str, Any]]],
    persona_dimensions: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    facet_lookup = {str(facet.get("facetKey") or facet.get("key")): facet for facet in facets}
    directives = meta.get("signalScans")
    if not isinstance(directives, list):
        return []
    judges: list[dict[str, Any]] = []
    for index, directive in enumerate(directives):
        judge = _aggregate_judge_directive(
            directive=directive,
            index=index,
            context_key=str(meta.get("key") or ""),
            facet_lookup=facet_lookup,
            field_values=field_values,
            persona_dimensions=persona_dimensions or {},
        )
        if judge:
            judges.append(judge)
    return judges


def _aggregate_judge_directive(
    *,
    directive: dict[str, Any],
    index: int,
    context_key: str,
    facet_lookup: dict[str, dict[str, Any]],
    field_values: dict[str, list[dict[str, Any]]],
    persona_dimensions: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    persona_dimensions = persona_dimensions or {}
    target_facet_key = str(directive.get("targetFacetKey") or "").strip()
    if not target_facet_key:
        return None
    target_field = facet_lookup.get(target_facet_key)
    if target_field is None:
        return None
    group_by_mode = str(directive.get("groupByMode") or "none").strip().lower()
    if group_by_mode not in JUDGE_GROUP_BY_MODES:
        group_by_mode = "none"
    group_by_facet_key = str(directive.get("groupByFacetKey") or "").strip() or None
    group_by_field = facet_lookup.get(group_by_facet_key) if group_by_facet_key else None
    persona_dimension = str(directive.get("groupByPersonaDimension") or "").strip() or None
    target_entries = [
        entry
        for entry in field_values.get(str(target_field.get("key")), [])
        if _has_value(entry.get("value")) and entry.get("trialName") is not None
    ]
    if not target_entries:
        return None

    bucket_map: dict[str, list[dict[str, Any]]] = {}
    if group_by_mode == "persona_attribute":
        if not persona_dimension:
            return None
        bucket_map = _persona_attribute_bucket_map(
            target_entries, persona_dimension, persona_dimensions
        )
        if not bucket_map:
            return None
    elif group_by_mode == "none" or group_by_field is None:
        bucket_map["All"] = target_entries
    elif group_by_mode == "categorical":
        group_entries = {
            str(entry.get("trialName")): _categorical_key(entry.get("value"))
            for entry in field_values.get(str(group_by_field.get("key")), [])
            if entry.get("trialName") is not None and _has_value(entry.get("value"))
        }
        for entry in target_entries:
            trial_name = str(entry.get("trialName"))
            bucket = group_entries.get(trial_name)
            if bucket is None:
                continue
            bucket_map.setdefault(bucket, []).append(entry)
    else:
        bands = _normalize_numeric_bands(directive.get("bands"))
        if not bands:
            # No explicit bands: auto-bin the numeric axis by its distribution.
            bands = _auto_numeric_bands(
                _numeric_axis_values(group_by_field, field_values)
            )
        if not bands:
            return None
        group_entries = {
            str(entry.get("trialName")): entry.get("value")
            for entry in field_values.get(str(group_by_field.get("key")), [])
            if entry.get("trialName") is not None and _has_value(entry.get("value"))
        }
        for entry in target_entries:
            trial_name = str(entry.get("trialName"))
            bucket = _match_numeric_band(group_entries.get(trial_name), bands)
            if bucket is None:
                continue
            bucket_map.setdefault(bucket, []).append(entry)

    buckets = [
        {
            "bucket": bucket,
            "count": len(entries),
            "samples": _sample_values(entries, limit=3),
        }
        for bucket, entries in sorted(
            bucket_map.items(),
            key=lambda item: (-len(item[1]), item[0]),
        )
    ]
    if not buckets:
        return None
    target_label = str(target_field.get("label") or target_facet_key)
    if group_by_mode == "persona_attribute" and persona_dimension:
        group_by_label = _humanize_persona_dimension(persona_dimension)
    else:
        group_by_label = str(
            (group_by_field.get("label") if isinstance(group_by_field, dict) else None)
            or group_by_facet_key
            or "All"
        )
    # Per-trial samples for the LLM to score independently (primary prevalence view).
    # The group label rides along so we can also produce an optional group breakdown.
    scan_samples: list[dict[str, Any]] = []
    for bucket in buckets:
        for entry in bucket_map.get(bucket["bucket"], []):
            text = _value_to_sample_string(entry.get("value"))
            if not text:
                continue
            scan_samples.append(
                {"id": len(scan_samples), "text": text, "group": bucket["bucket"]}
            )

    judge_kind = str(directive.get("judgeKind") or "llm_signal_judge").strip()
    return {
        "id": str(directive.get("id") or "{}.judge_{}".format(context_key, index + 1)),
        "title": str(directive.get("title") or "{} judge by {}".format(target_label, group_by_label)),
        "targetFacetKey": target_facet_key,
        "groupByFacetKey": group_by_facet_key,
        "groupByPersonaDimension": persona_dimension,
        "groupByLabel": group_by_label,
        "groupByMode": group_by_mode,
        "lens": _directive_lens(directive, group_by_mode=group_by_mode),
        "judgeKind": judge_kind,
        "prompt": directive.get("prompt"),
        "rubric": directive.get("rubric"),
        "signals": _normalize_signals(directive.get("signals")),
        "status": "ready_for_llm" if judge_kind.startswith("llm_") else "heuristic",
        "overall": {
            "count": len(target_entries),
            "samples": _sample_values(target_entries, limit=5),
        },
        "total": len(scan_samples),
        "signalStats": [],
        "scanSamples": scan_samples,
        "buckets": buckets,
    }


def _facet_key_leaf(facet: dict[str, Any]) -> str:
    raw = str(facet.get("facetKey") or facet.get("key") or "").strip()
    if not raw:
        return ""
    return raw.split(".")[-1].replace("-", "_")


def _fmt_scale_value(value: float) -> str:
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:.1f}"


def _numeric_bucket_labels(count: int) -> list[str]:
    if count <= 1:
        return ["All"]
    if count == 2:
        return ["Lower", "Higher"]
    if count == 3:
        return ["Low", "Medium", "High"]
    return [f"Band {index + 1}" for index in range(count)]


def _auto_numeric_bands(
    values: list[Any], *, target_buckets: int = 3
) -> list[dict[str, Any]]:
    """Distribution-based (equal-frequency) bins for a numeric grouping axis.

    Splits the observed values into up to ``target_buckets`` quantile groups of
    roughly equal size, keeping equal values in the same bucket. Labels carry the
    real observed value span (e.g. ``Low (1-3)``). Returns ``[]`` when the field
    is constant or otherwise not worth splitting.
    """
    numbers = sorted(
        float(value)
        for value in values
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    )
    if not numbers:
        return []
    distinct = sorted(set(numbers))
    if len(distinct) < 2:
        return []

    buckets = min(target_buckets, len(distinct))
    counts = Counter(numbers)
    total = len(numbers)
    target = total / buckets

    groups: list[list[float]] = []
    current: list[float] = []
    running = 0
    for index, value in enumerate(distinct):
        current.append(value)
        running += counts[value]
        remaining_values = len(distinct) - (index + 1)
        if (
            len(groups) < buckets - 1
            and running >= target
            and remaining_values >= buckets - len(groups) - 1
        ):
            groups.append(current)
            current = []
            running = 0
    if current:
        groups.append(current)
    if len(groups) < 2:
        return []

    labels = _numeric_bucket_labels(len(groups))
    bands: list[dict[str, Any]] = []
    for group_index, group in enumerate(groups):
        group_min, group_max = group[0], group[-1]
        span = (
            _fmt_scale_value(group_min)
            if group_min == group_max
            else f"{_fmt_scale_value(group_min)}-{_fmt_scale_value(group_max)}"
        )
        bands.append(
            {
                "label": f"{labels[group_index]} ({span})",
                "min": None if group_index == 0 else group_min,
                "max": None if group_index == len(groups) - 1 else group_max,
            }
        )
    return bands


def _categorical_axis_sizes(
    facet: dict[str, Any], field_values: dict[str, list[dict[str, Any]]]
) -> list[int]:
    counts: Counter[str] = Counter()
    for entry in field_values.get(str(facet.get("key")), []):
        if entry.get("trialName") is None or not _has_value(entry.get("value")):
            continue
        counts[_categorical_key(entry.get("value"))] += 1
    return list(counts.values())


def _numeric_axis_values(
    facet: dict[str, Any], field_values: dict[str, list[dict[str, Any]]]
) -> list[float]:
    values: list[float] = []
    for entry in field_values.get(str(facet.get("key")), []):
        if entry.get("trialName") is None or not _has_value(entry.get("value")):
            continue
        raw = entry.get("value")
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            values.append(float(raw))
    return values


def _axis_record(
    facet: dict[str, Any], mode: str, bands: list[dict[str, Any]] | None
) -> dict[str, Any]:
    return {
        "facet": facet,
        "key": str(facet.get("key")),
        "facetKey": str(facet.get("facetKey") or facet.get("key") or ""),
        "mode": mode,
        "bands": bands,
    }


def _resolve_explained_axis(
    text_facet: dict[str, Any],
    facets: list[dict[str, Any]],
    field_values: dict[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    """Group axis for a textual facet, taken from its explicit ``explainsFacetKey``.

    The binding is authored in the self-report schema (``explanation:`` under the
    measured field) or emitted directly by a verifier — never guessed. Numeric
    targets are auto-binned by their distribution; categorical targets group by
    value. Returns ``None`` when there is no declared target or the target does
    not split the cohort into >= 2 non-empty groups.
    """
    target_leaf = str(text_facet.get("explainsFacetKey") or "").strip()
    if not target_leaf:
        return None
    target = next(
        (
            facet
            for facet in facets
            if facet is not text_facet and _facet_key_leaf(facet) == target_leaf
        ),
        None,
    )
    if target is None:
        return None
    kind = target.get("kind")
    if kind == "numerical":
        bands = _auto_numeric_bands(_numeric_axis_values(target, field_values))
        if len(bands) < 2:
            return None
        return _axis_record(target, "numeric_band", bands)
    if kind == "categorical":
        nonempty = [size for size in _categorical_axis_sizes(target, field_values) if size > 0]
        if len(nonempty) < 2:
            return None
        return _axis_record(target, "categorical", None)
    return None


def _aggregate_context_cross_facet_views(
    *,
    facets: list[dict[str, Any]],
    field_values: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Raw-quote preview of each explanation grouped by its declared target axis.

    The axis for every textual facet comes from its explicit ``explainsFacetKey``
    binding (schema ``explanation:`` sub-field, or verifier-emitted). Facets with
    no declared target get no grouped preview — no heuristic axis guessing.
    """
    # Fixed labels / non-persona prose should not become Common quote groups.
    skip_text_leaves = {"task_goal_label"}
    cross_facet_views: list[dict[str, Any]] = []
    for facet in facets:
        if facet.get("kind") != "textual":
            continue
        role = str(facet.get("role") or "")
        if role not in {"explanation", "evidence", "supporting_text"}:
            continue
        if _facet_key_leaf(facet) in skip_text_leaves:
            continue
        axis = _resolve_explained_axis(facet, facets, field_values)
        if axis is None:
            continue
        axis_key = str(axis.get("key"))
        axis_bands = axis.get("bands")
        if str(axis.get("mode")) == "numeric_band" and axis_bands:
            group_entries = {
                str(entry.get("trialName")): _match_numeric_band(entry.get("value"), axis_bands)
                for entry in field_values.get(axis_key, [])
                if entry.get("trialName") is not None and _has_value(entry.get("value"))
            }
            group_entries = {
                trial: bucket for trial, bucket in group_entries.items() if bucket is not None
            }
            band_order = {str(band.get("label")): index for index, band in enumerate(axis_bands)}
        else:
            group_entries = {
                str(entry.get("trialName")): _categorical_key(entry.get("value"))
                for entry in field_values.get(axis_key, [])
                if entry.get("trialName") is not None and _has_value(entry.get("value"))
            }
            band_order = None
        if not group_entries:
            continue
        buckets: dict[str, list[str]] = {}
        for entry in field_values.get(str(facet.get("key")), []):
            trial_name = str(entry.get("trialName") or "")
            bucket = group_entries.get(trial_name)
            value = str(entry.get("value") or "").strip()
            if not bucket or not value:
                continue
            buckets.setdefault(bucket, []).append(value)
        if not buckets:
            continue
        unique_values = {value for values in buckets.values() for value in values}
        total_values = sum(len(values) for values in buckets.values())
        # Low-diversity text (one or two templated notes repeated across the
        # cohort) just echoes the same quote in every bucket — not a useful
        # Common analysis grouping.
        if len(unique_values) <= 2 and total_values > 2:
            continue
        if band_order is not None:
            ordered_buckets = sorted(
                buckets.items(),
                key=lambda item: band_order.get(item[0], len(band_order)),
            )
        else:
            ordered_buckets = sorted(
                buckets.items(),
                key=lambda item: (-len(item[1]), item[0]),
            )
        cross_facet_views.append(
            {
                "type": "text_by_primary_category",
                "primaryFacetKey": str(axis.get("facetKey") or axis_key),
                "textFacetKey": facet.get("key"),
                "buckets": [
                    {
                        "category": category,
                        "count": len(values),
                        "samples": list(dict.fromkeys(values))[:3],
                    }
                    for category, values in ordered_buckets
                ],
            }
        )
    return cross_facet_views


def _normalize_numeric_bands(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        if not label:
            continue
        normalized.append(
            {
                "label": label,
                "min": item.get("min"),
                "max": item.get("max"),
            }
        )
    return normalized


def _normalize_signals(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    signals: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "").strip()
        if not key:
            continue
        signals.append(
            {
                "key": key,
                "label": item.get("label") or key,
                "valueType": item.get("valueType"),
                "description": item.get("description"),
            }
        )
    return signals


def _match_numeric_band(value: Any, bands: list[dict[str, Any]]) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    for band in bands:
        lower = band.get("min")
        upper = band.get("max")
        if lower is not None and numeric < float(lower):
            continue
        if upper is not None and numeric > float(upper):
            continue
        return str(band["label"])
    return None


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return len(value) > 0
    return True


def _aggregate_numerical(entries: list[dict[str, Any]]) -> dict[str, Any]:
    numbers: list[float] = []
    for entry in entries:
        raw = entry.get("value")
        if isinstance(raw, bool):
            continue
        if isinstance(raw, (int, float)):
            numbers.append(float(raw))
    if not numbers:
        return {
            "count": 0,
            "min": None,
            "max": None,
            "avg": None,
            "std": None,
            "counts": [],
        }
    avg = mean(numbers)
    variance = mean([(value - avg) ** 2 for value in numbers]) if len(numbers) > 1 else 0.0
    value_counts: Counter[str] = Counter()
    for value in numbers:
        # Prefer integer labels for likert-style whole numbers.
        key = str(int(value)) if float(value).is_integer() else str(value)
        value_counts[key] += 1
    ranked_counts = [
        {"value": value, "count": count}
        for value, count in sorted(
            value_counts.items(),
            key=lambda item: (
                float(item[0]) if _is_number(item[0]) else 0.0,
                item[0],
            ),
        )
    ]
    return {
        "count": len(numbers),
        "min": min(numbers),
        "max": max(numbers),
        "avg": round(avg, 4),
        "std": round(math.sqrt(variance), 4),
        "counts": ranked_counts,
    }


def _is_number(value: str) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _aggregate_categorical(entries: list[dict[str, Any]]) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    for entry in entries:
        raw = entry.get("value")
        if isinstance(raw, list):
            for item in raw:
                counts[_categorical_key(item)] += 1
        else:
            counts[_categorical_key(raw)] += 1
    ranked = [
        {"value": value, "count": count}
        for value, count in counts.most_common()
    ]
    return {
        "count": sum(counts.values()),
        "distinctCount": len(counts),
        "counts": ranked,
    }


def _categorical_key(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "(missing)"
    return str(value)


_MAX_FREE_TEXT_THEMES = 6
# Generic English function words only — domain terms are handled by TF-IDF IDF.
_TFIDF_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "into",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "to",
        "with",
        "without",
    }
)


def _normalize_text_theme(value: str) -> str:
    compact = " ".join(str(value or "").lower().split())
    compact = re.sub(r"[^\w\s]", "", compact)
    return compact.strip()


def _tfidf_terms(value: str) -> list[str]:
    tokens: list[str] = []
    for raw in _normalize_text_theme(value).split():
        if len(raw) <= 1 or raw in _TFIDF_STOPWORDS:
            continue
        token = raw
        # Light plural normalization only (not domain aliases).
        if len(token) > 4 and token.endswith("es") and not token.endswith(("ss", "ous", "ies")):
            token = token[:-2]
        elif len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "us", "is", "ous", "ing")):
            token = token[:-1]
        if len(token) > 1 and token not in _TFIDF_STOPWORDS:
            tokens.append(token)
    terms = list(tokens)
    for index in range(len(tokens) - 1):
        terms.append("{} {}".format(tokens[index], tokens[index + 1]))
    return terms


def _tfidf_vectors(documents: list[str]) -> list[list[float]]:
    """Lightweight TF-IDF (unigram + bigram), L2-normalized. Fast for survey-scale n."""
    docs_terms = [_tfidf_terms(document) for document in documents]
    document_frequency: Counter[str] = Counter()
    for terms in docs_terms:
        document_frequency.update(set(terms))
    vocabulary = sorted(document_frequency.keys())
    if not vocabulary:
        return [[0.0] for _ in documents]
    index = {term: position for position, term in enumerate(vocabulary)}
    n_docs = len(documents)
    matrix: list[list[float]] = []
    for terms in docs_terms:
        tf_counts = Counter(terms)
        length = max(1, sum(tf_counts.values()))
        row = [0.0] * len(vocabulary)
        for term, count in tf_counts.items():
            idf = math.log((1.0 + n_docs) / (1.0 + document_frequency[term])) + 1.0
            row[index[term]] = (count / length) * idf
        norm = math.sqrt(sum(value * value for value in row)) or 1.0
        matrix.append([value / norm for value in row])
    return matrix


def _cosine_similarity_matrix(vectors: list[list[float]]) -> list[list[float]]:
    n = len(vectors)
    sim = [[0.0] * n for _ in range(n)]
    for i in range(n):
        sim[i][i] = 1.0
        left = vectors[i]
        for j in range(i + 1, n):
            right = vectors[j]
            score = sum(a * b for a, b in zip(left, right))
            # Numerical guard.
            score = 0.0 if score < 0 else (1.0 if score > 1.0 else score)
            sim[i][j] = score
            sim[j][i] = score
    return sim


def _average_linkage_labels(sim: list[list[float]], k: int) -> list[int]:
    """Greedy average-linkage clustering down to k clusters."""
    n = len(sim)
    if n == 0:
        return []
    k = max(1, min(k, n))
    clusters: list[list[int]] = [[index] for index in range(n)]
    while len(clusters) > k:
        best_i = 0
        best_j = 1
        best_score = -1.0
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                total = 0.0
                pairs = 0
                for left in clusters[i]:
                    for right in clusters[j]:
                        total += sim[left][right]
                        pairs += 1
                score = total / pairs if pairs else 0.0
                if score > best_score:
                    best_score = score
                    best_i = i
                    best_j = j
        merged = clusters[best_i] + clusters[best_j]
        clusters = [cluster for index, cluster in enumerate(clusters) if index not in {best_i, best_j}]
        clusters.append(merged)
    labels = [0] * n
    for label, members in enumerate(clusters):
        for index in members:
            labels[index] = label
    return labels


def _agglomerative_merge_heights(sim: list[list[float]]) -> list[float]:
    """Average-linkage merge similarities from n clusters down to 1."""
    n = len(sim)
    if n <= 1:
        return []
    clusters: list[list[int]] = [[index] for index in range(n)]
    heights: list[float] = []
    while len(clusters) > 1:
        best_i = 0
        best_j = 1
        best_score = -1.0
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                total = 0.0
                pairs = 0
                for left in clusters[i]:
                    for right in clusters[j]:
                        total += sim[left][right]
                        pairs += 1
                score = total / pairs if pairs else 0.0
                if score > best_score:
                    best_score = score
                    best_i = i
                    best_j = j
        heights.append(best_score)
        merged = clusters[best_i] + clusters[best_j]
        clusters = [cluster for index, cluster in enumerate(clusters) if index not in {best_i, best_j}]
        clusters.append(merged)
    return heights


def _choose_optimal_theme_labels(sim: list[list[float]], weights: list[int]) -> list[int]:
    """
    Choose k from the largest drop in agglomerative merge similarity
    (dendrogram gap). This is data-driven and avoids silhouette's bias
    toward too many clusters on short TF-IDF texts.
    """
    del weights
    n = len(sim)
    if n <= 1:
        return [0] * n

    heights = _agglomerative_merge_heights(sim)
    # heights[m] = similarity used to go from (n-m) -> (n-m-1) clusters.
    best_merges = n - 1
    best_gap = float("-inf")
    for merge_count in range(1, n):
        prev_height = heights[merge_count - 1]
        next_height = heights[merge_count] if merge_count < len(heights) else 0.0
        gap = prev_height - next_height
        k_after = n - merge_count
        if k_after < 1 or k_after > _MAX_FREE_TEXT_THEMES:
            continue
        # Prefer clearer gaps; tiny ties break toward fewer themes.
        score = gap + 0.01 * (1.0 / k_after)
        if score > best_gap:
            best_gap = score
            best_merges = merge_count

    gap_k = max(1, min(_MAX_FREE_TEXT_THEMES, n - best_merges))
    return _average_linkage_labels(sim, gap_k)


def _cluster_text_values(values: list[str]) -> list[dict[str, Any]]:
    """Cluster free-text answers with TF-IDF cosine similarity and automatic k."""
    cleaned = [" ".join(str(value or "").split()).strip() for value in values]
    cleaned = [text for text in cleaned if text]
    if not cleaned:
        return []

    # Collapse exact normalized duplicates first (punctuation/case only).
    seed_buckets: dict[str, dict[str, Any]] = {}
    for text in cleaned:
        key = _normalize_text_theme(text) or text.lower()
        bucket = seed_buckets.get(key)
        if bucket is None:
            bucket = {"count": 0, "label_counts": Counter(), "representative": text}
            seed_buckets[key] = bucket
        bucket["count"] += 1
        bucket["label_counts"][text] += 1

    seeds = list(seed_buckets.values())
    n = len(seeds)
    if n == 1:
        label_counts: Counter[str] = seeds[0]["label_counts"]
        ordered = sorted(label_counts.items(), key=lambda item: (-item[1], len(item[0]), item[0]))
        return [
            {
                "value": ordered[0][0],
                "count": int(seeds[0]["count"]),
                "samples": [text for text, _count in ordered[:3]],
            }
        ]

    documents = []
    for seed in seeds:
        label_counts = seed["label_counts"]
        ordered = sorted(label_counts.items(), key=lambda item: (-item[1], len(item[0]), item[0]))
        documents.append(ordered[0][0])
        seed["representative"] = ordered[0][0]

    vectors = _tfidf_vectors(documents)
    sim = _cosine_similarity_matrix(vectors)
    weights = [int(seed["count"]) for seed in seeds]
    labels = _choose_optimal_theme_labels(sim, weights)

    merged: dict[int, dict[str, Any]] = {}
    for index, label in enumerate(labels):
        bucket = merged.get(label)
        if bucket is None:
            bucket = {"count": 0, "label_counts": Counter()}
            merged[label] = bucket
        bucket["count"] += int(seeds[index]["count"])
        bucket["label_counts"].update(seeds[index]["label_counts"])

    ranked: list[dict[str, Any]] = []
    for bucket in merged.values():
        label_counts = bucket["label_counts"]
        ordered = sorted(label_counts.items(), key=lambda item: (-item[1], len(item[0]), item[0]))
        ranked.append(
            {
                "value": ordered[0][0],
                "count": int(bucket["count"]),
                "samples": [text for text, _count in ordered[:3]],
            }
        )
    ranked.sort(key=lambda item: (-int(item["count"]), str(item["value"])))
    return ranked


def _prose_theme_summary(answer_count: int, ranked_counts: list[dict[str, Any]]) -> str | None:
    """Write a short narrative rollup — theme chips carry the full inventory."""
    if answer_count <= 0 or not ranked_counts:
        return None
    if len(ranked_counts) == 1:
        return 'All {} answers converge on one theme: "{}".'.format(
            answer_count,
            str(ranked_counts[0]["value"]),
        )

    primary = ranked_counts[0]
    secondary = ranked_counts[1]
    primary_count = int(primary["count"])
    secondary_count = int(secondary["count"])
    primary_label = str(primary["value"])
    secondary_label = str(secondary["value"])
    smaller = ranked_counts[2:]
    smaller_answers = sum(int(item["count"]) for item in smaller)

    if primary_count + secondary_count >= max(2, int(round(answer_count * 0.65))):
        summary = (
            'Across {} answers, the dominant themes are "{}" ({}) and "{}" ({}).'.format(
                answer_count,
                primary_label,
                primary_count,
                secondary_label,
                secondary_count,
            )
        )
        if smaller_answers > 0:
            summary = summary[:-1] + ", with {} more in {} smaller theme{}.".format(
                smaller_answers,
                len(smaller),
                "" if len(smaller) == 1 else "s",
            )
        return summary

    summary = (
        'Across {} answers, responses form {} themes. The largest is "{}" ({}), '
        'followed by "{}" ({}).'.format(
            answer_count,
            len(ranked_counts),
            primary_label,
            primary_count,
            secondary_label,
            secondary_count,
        )
    )
    if smaller_answers > 0:
        summary += " The remaining {} answers fall into {} smaller theme{}.".format(
            smaller_answers,
            len(smaller),
            "" if len(smaller) == 1 else "s",
        )
    return summary


def _aggregate_textual(entries: list[dict[str, Any]]) -> dict[str, Any]:
    values = [str(entry.get("value") or "").strip() for entry in entries if str(entry.get("value") or "").strip()]
    ranked_counts = _cluster_text_values(values)
    unique_count = len(ranked_counts)
    # One representative sample per theme (not a global top-N dump).
    samples = [str(item["value"]) for item in ranked_counts[:8]]
    summary = _prose_theme_summary(len(values), ranked_counts)
    return {
        "count": len(values),
        "uniqueCount": unique_count,
        "samples": samples,
        "counts": ranked_counts,
        "summary": summary,
        "summaryType": "heuristic" if summary else None,
    }


def _sample_values(entries: list[dict[str, Any]], *, limit: int) -> list[str]:
    values: list[str] = []
    for entry in entries:
        rendered = _value_to_sample_string(entry.get("value"))
        if not rendered:
            continue
        if rendered in values:
            continue
        values.append(rendered)
        if len(values) >= limit:
            break
    return values


def _value_to_sample_string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return _shorten(value)
    if isinstance(value, (int, float, bool)):
        return str(value)
    try:
        return _shorten(json.dumps(value, ensure_ascii=False, sort_keys=True))
    except TypeError:
        return _shorten(str(value))


def _shorten(value: str, *, limit: int = 2000) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"
