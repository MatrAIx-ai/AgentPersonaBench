"""Load and validate per-task ``persona_strategy.json`` (Playground sampling defaults)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PERSONA_STRATEGY_FILENAME = "persona_strategy.json"
PERSONA_SAMPLING_MODES = frozenset({"single", "random", "stratified", "all"})
STRATIFIED_ALLOCATIONS = frozenset({"perCell", "proportional", "equalTotal"})

# Removed flat strategy keys — use ``sampling`` instead.
_REMOVED_STRATEGY_KEYS = frozenset(
    {
        "defaultMode",
        "stratifyFields",
        "sampleSize",
        "sampleSizePerValueGroup",
        "personaId",
    }
)

# Minimal stub when scaffolding a new task — replace filters with the product cohort.
DEFAULT_PERSONA_STRATEGY: dict[str, Any] = {
    "schemaVersion": "1.0",
    "sources": [],
    "dimensionFilters": {},
    "sampling": {"mode": "random", "sampleSize": 4},
}


def persona_strategy_path(task_dir: Path) -> Path:
    return task_dir / PERSONA_STRATEGY_FILENAME


def load_persona_strategy(task_dir: Path) -> dict[str, Any] | None:
    """Return a normalized strategy dict, or ``None`` when the file is absent/invalid.

    Application tasks under ``application/tasks/`` are expected to ship the file
    (CI enforces presence). Loaders still tolerate missing files for ad-hoc paths.
    """
    path = persona_strategy_path(task_dir)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    return normalize_persona_strategy(raw)


def normalize_persona_strategy(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a strategy that already uses the unified ``sampling`` block."""
    schema_version = str(raw.get("schemaVersion") or "1.0").strip() or "1.0"
    pool = str(raw.get("pool") or "").strip() or None
    sources = _as_str_list(raw.get("sources"))
    dimension_filters = _as_dimension_filters(raw.get("dimensionFilters"))

    seed = raw.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, (int, float)):
        seed = None
    else:
        seed = int(seed)

    cohort_id = str(raw.get("cohortId") or "").strip() or None
    sampling_raw = raw.get("sampling")
    sampling = (
        _normalize_sampling_block(sampling_raw)
        if isinstance(sampling_raw, dict)
        else {"mode": "random", "sampleSize": 4}
    )

    payload: dict[str, Any] = {
        "schemaVersion": schema_version,
        "sources": sources,
        "dimensionFilters": dimension_filters,
        "sampling": sampling,
    }
    if pool:
        payload["pool"] = pool
    if seed is not None:
        payload["seed"] = seed
    if cohort_id:
        payload["cohortId"] = cohort_id
    return payload


def validate_persona_strategy_file(
    task_dir: Path,
    *,
    require_cohort: bool = True,
) -> list[str]:
    """Return human-readable errors for a task's ``persona_strategy.json``.

    The file is **required** for application tasks. Field values may use defaults
    (see ``DEFAULT_PERSONA_STRATEGY``), but tasks are expected to declare a
    target cohort via ``dimensionFilters`` and/or ``cohortId`` when
    ``require_cohort`` is true.
    """
    errors: list[str] = []
    path = persona_strategy_path(task_dir)
    rel = str(path)
    if not path.is_file():
        errors.append(
            f"{rel}: missing required persona_strategy.json "
            "(declare Playground sampling defaults / target cohort)"
        )
        return errors

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        errors.append(f"{rel}: cannot read file ({exc})")
        return errors
    except json.JSONDecodeError as exc:
        errors.append(f"{rel}: invalid JSON ({exc})")
        return errors

    if not isinstance(raw, dict):
        errors.append(f"{rel}: root value must be a JSON object")
        return errors

    if "schemaVersion" not in raw or not str(raw.get("schemaVersion") or "").strip():
        errors.append(f'{rel}: schemaVersion is required (use "1.0")')

    removed = sorted(key for key in _REMOVED_STRATEGY_KEYS if key in raw)
    if removed:
        errors.append(
            f"{rel}: remove legacy fields {', '.join(removed)}; "
            "put mode / quotas under sampling "
            '(e.g. sampling.mode, sampling.allocation, sampling.perCell)'
        )

    raw_sampling = raw.get("sampling")
    if not isinstance(raw_sampling, dict):
        errors.append(
            f"{rel}: sampling object is required "
            '(e.g. {{"mode":"random","sampleSize":4}})'
        )
        return errors

    normalized = normalize_persona_strategy(raw)
    sampling = normalized.get("sampling") or {}
    mode = sampling.get("mode")
    if mode not in PERSONA_SAMPLING_MODES:
        errors.append(
            f"{rel}: sampling.mode is required "
            f"(one of: {', '.join(sorted(PERSONA_SAMPLING_MODES))})"
        )

    if require_cohort:
        filters = normalized.get("dimensionFilters") or {}
        cohort_id = normalized.get("cohortId")
        has_filters = isinstance(filters, dict) and any(
            isinstance(vals, list) and len(vals) > 0 for vals in filters.values()
        )
        if not has_filters and not cohort_id:
            errors.append(
                f"{rel}: declare a target cohort via non-empty dimensionFilters "
                "and/or cohortId (most tasks filter to a product audience)"
            )

    if mode == "random":
        sample_size = sampling.get("sampleSize")
        if not isinstance(sample_size, int) or sample_size < 1:
            errors.append(f'{rel}: sampling.mode "random" requires sampleSize >= 1')
    elif mode == "stratified":
        # Validate quotas against the author-authored block so normalize cannot
        # silently drop a conflicting sampleSize / perCell before we complain.
        errors.extend(
            _validate_stratified_sampling(rel, normalized, sampling, raw_sampling)
        )

    return errors


def _validate_stratified_sampling(
    rel: str,
    normalized: dict[str, Any],
    sampling: dict[str, Any],
    raw_sampling: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    fields = sampling.get("fields") or []
    if not fields:
        errors.append(f'{rel}: sampling.mode "stratified" requires sampling.fields')

    allocation = sampling.get("allocation")
    if allocation not in STRATIFIED_ALLOCATIONS:
        errors.append(
            f"{rel}: stratified sampling.allocation is required "
            f"(one of: {', '.join(sorted(STRATIFIED_ALLOCATIONS))})"
        )

    filters = normalized.get("dimensionFilters") or {}
    missing_axes = [
        field for field in fields if field not in filters or not filters.get(field)
    ]
    if missing_axes:
        errors.append(
            f"{rel}: every sampling.fields entry must also appear in "
            f"dimensionFilters with allowed values (missing: {', '.join(missing_axes)}); "
            "otherwise Playground cannot guarantee cell coverage or synthesize gaps"
        )

    if allocation == "perCell":
        per_cell = sampling.get("perCell")
        if not isinstance(per_cell, int) or per_cell < 1:
            errors.append(
                f'{rel}: allocation "perCell" requires sampling.perCell >= 1'
            )
        if raw_sampling.get("sampleSize") is not None:
            errors.append(
                f'{rel}: allocation "perCell" must not set sampling.sampleSize '
                "(total follows from perCell × cells)"
            )
    elif allocation in {"proportional", "equalTotal"}:
        sample_size = sampling.get("sampleSize")
        if not isinstance(sample_size, int) or sample_size < 1:
            errors.append(
                f'{rel}: allocation "{allocation}" requires sampling.sampleSize >= 1'
            )
        if raw_sampling.get("perCell") is not None:
            errors.append(
                f'{rel}: allocation "{allocation}" must not set sampling.perCell'
            )
        if (
            allocation == "equalTotal"
            and isinstance(sample_size, int)
            and not missing_axes
            and fields
        ):
            try:
                from matraix.persona_generator import (
                    build_filter_strata,
                    filter_feasible_strata,
                )

                stratify_filters = {field: list(filters[field]) for field in fields}
                strata = build_filter_strata(stratify_filters, max_strata=2048)
                feasible, _dropped = filter_feasible_strata(strata)
                min_cells = len(feasible)
                if min_cells and int(sample_size) < min_cells:
                    errors.append(
                        f"{rel}: sampleSize={sample_size} is below the stratified "
                        f"cell count={min_cells} (need ≥1 per combination of "
                        f"{', '.join(fields)}). Raise sampleSize, or switch to "
                        'allocation "perCell".'
                    )
            except Exception:  # noqa: BLE001 — soft: skip when schema/generator unavailable
                pass

    return errors


def _normalize_sampling_block(raw: dict[str, Any]) -> dict[str, Any]:
    mode = str(raw.get("mode") or "").strip().lower()
    if mode not in PERSONA_SAMPLING_MODES:
        mode = "random"

    if mode == "single":
        block: dict[str, Any] = {"mode": "single"}
        persona_id = str(raw.get("personaId") or "").strip()
        if persona_id:
            block["personaId"] = persona_id
        return block

    if mode == "all":
        return {"mode": "all"}

    if mode == "random":
        sample_size = _as_positive_int(raw.get("sampleSize"))
        return {"mode": "random", "sampleSize": sample_size or 4}

    fields = _as_str_list(raw.get("fields"))
    allocation = str(raw.get("allocation") or "").strip()
    if allocation == "per_cell":
        allocation = "perCell"
    if allocation == "equal_total":
        allocation = "equalTotal"
    if allocation not in STRATIFIED_ALLOCATIONS:
        allocation = (
            "perCell" if _as_positive_int(raw.get("perCell")) else "equalTotal"
        )

    block = {
        "mode": "stratified",
        "fields": fields,
        "allocation": allocation,
    }
    if allocation == "perCell":
        block["perCell"] = _as_positive_int(raw.get("perCell")) or 1
    else:
        block["sampleSize"] = _as_positive_int(raw.get("sampleSize")) or 1
    return block


def sampling_to_pool_kwargs(sampling: dict[str, Any] | None) -> dict[str, Any]:
    """Map unified ``sampling`` to ``PersonaPoolService.sample_pool`` kwargs."""
    block = sampling if isinstance(sampling, dict) else {}
    mode = str(block.get("mode") or "random").strip().lower()
    allocation = str(block.get("allocation") or "").strip() or None
    out: dict[str, Any] = {
        "mode": mode,
        "allocation": allocation,
        "stratify_fields": list(block.get("fields") or []) or None,
        "sample_size": _as_positive_int(block.get("sampleSize")),
        "sample_size_per_value_group": None,
        "use_entire_pool": mode == "all",
        "persona_id": str(block.get("personaId") or "").strip() or None,
    }
    if mode == "stratified" and allocation == "perCell":
        out["sample_size_per_value_group"] = _as_positive_int(block.get("perCell")) or 1
    elif mode == "stratified" and allocation in {"proportional", "equalTotal"}:
        out["sample_size"] = _as_positive_int(block.get("sampleSize")) or 1
        out["sample_size_per_value_group"] = None
        out["allocation"] = allocation
    elif mode == "random":
        out["sample_size"] = _as_positive_int(block.get("sampleSize")) or 4
        out["stratify_fields"] = None
    return out


def _as_positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = int(value)
    return number if number >= 1 else None


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _as_dimension_filters(value: object) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, list[str]] = {}
    for key, raw in value.items():
        dim = str(key).strip()
        if not dim:
            continue
        if isinstance(raw, list):
            values = [str(item).strip() for item in raw if str(item).strip()]
        elif raw is None:
            values = []
        else:
            text = str(raw).strip()
            values = [text] if text else []
        if values:
            out[dim] = values
    return out
