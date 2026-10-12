"""Build multi-persona Harbor job configs for dimension grounding runs."""

from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any, Callable

import yaml

from matraix.persona_dimension_catalog import values_for_dimension
from matraix.task_catalog import (
    confounder_values_from_grounding,
    get_task_grounding_spec,
    probe_dimension_from_grounding,
)

DEFAULT_DATASET = "persona/datasets/matraix-persona-dev-sample"
DEFAULT_STRATIFY_FIELDS = ["dimensions.economic_motivation"]
SMOKE_PERSONA_ID = "0001"
SMOKE_PERSONA_PATH = f"{DEFAULT_DATASET}/persona_{SMOKE_PERSONA_ID}.yaml"
DEFAULT_GROUNDING_JOBS_DIR = "configs/jobs/persona-job-recipe"
GENERATED_COHORTS_DIR = "persona/datasets/_generated/cohorts"
DEFAULT_DIMENSIONS_SCHEMA = "persona/schema/dimensions.json"


def get_nested(data: dict[str, Any], dotted_path: str) -> Any:
    current: Any = data
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def probe_dimension_key(probe_dimension: str) -> str:
    return probe_dimension.split(".")[-1]


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "value"


def load_manifest(pool_dir: Path, *, repo_root: Path) -> list[dict[str, Any]]:
    manifest_path = pool_dir / "manifest.json"
    if manifest_path.is_file():
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries: list[dict[str, Any]] = []
        for item in payload.get("personas", []):
            if isinstance(item, dict):
                entries.append(item)
                continue
            if isinstance(item, str):
                path = pool_dir / item
                raw = yaml.safe_load(path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    entries.append(
                        {
                            "persona_id": raw.get("persona_id"),
                            "path": str(path.relative_to(repo_root)),
                            **raw,
                        }
                    )
        return entries

    entries: list[dict[str, Any]] = []
    for path in sorted(pool_dir.glob("persona_*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            continue
        entries.append(
            {
                "persona_id": raw.get("persona_id"),
                "path": str(path.relative_to(repo_root)),
                **raw,
            }
        )
    return entries


def get_persona_field_value(
    entry: dict[str, Any],
    field_path: str,
    *,
    repo_root: Path,
) -> Any:
    """Read a dotted persona field from manifest entry or YAML file.

    Bare dimension ids (e.g. ``age_bracket``) resolve via ``dimensions.<id>`` so
    Playground strategies and filter UIs can pass catalog ids without a prefix.
    Explicit dotted paths (e.g. ``dimensions.age_bracket``) still work.
    """
    candidates = [field_path]
    if "." not in field_path:
        candidates.append(f"dimensions.{field_path}")

    for path in candidates:
        if path.split(".")[0] in entry:
            value = get_nested(entry, path)
            if value is not None:
                return value

    rel = entry.get("path")
    if not rel:
        return None
    raw = yaml.safe_load((repo_root / rel).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return None
    for path in candidates:
        value = get_nested(raw, path)
        if value is not None:
            return value
    return None


def get_persona_dimension_value(
    entry: dict[str, Any],
    probe_dimension: str,
    *,
    repo_root: Path,
) -> Any:
    return get_persona_field_value(entry, probe_dimension, repo_root=repo_root)


def _stratify_bucket_key(
    entry: dict[str, Any],
    stratify_fields: list[str],
    *,
    repo_root: Path,
) -> str | None:
    parts: list[str] = []
    for field in stratify_fields:
        value = get_persona_field_value(entry, field, repo_root=repo_root)
        if value is None:
            return None
        parts.append(str(value))
    return "\x1f".join(parts)


def filter_personas(
    entries: list[dict[str, Any]],
    *,
    probe_dimension: str,
    probe_value: str,
    repo_root: Path,
) -> list[dict[str, Any]]:
    matched: list[dict[str, Any]] = []
    for entry in entries:
        if probe_dimension.split(".")[0] in entry:
            value = get_nested(entry, probe_dimension)
        else:
            raw = yaml.safe_load(
                (repo_root / entry["path"]).read_text(encoding="utf-8")
            )
            if not isinstance(raw, dict):
                continue
            value = get_nested(raw, probe_dimension)
        if value == probe_value:
            matched.append(entry)
    return matched


def sample_personas_stratified(
    entries: list[dict[str, Any]],
    *,
    stratify_fields: list[str],
    sample_size_per_value_group: int,
    seed: int,
    repo_root: Path,
) -> list[dict[str, Any]]:
    """Sample *sample_size_per_value_group* personas from each stratify bucket."""
    if not stratify_fields:
        raise ValueError("stratify_fields must not be empty")
    if sample_size_per_value_group < 1:
        raise ValueError("sample_size_per_value_group must be >= 1")

    buckets: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        key = _stratify_bucket_key(entry, stratify_fields, repo_root=repo_root)
        if key is None:
            continue
        buckets.setdefault(key, []).append(entry)
    if not buckets:
        label = ", ".join(stratify_fields)
        raise ValueError(f"No personas with stratify fields ({label})")

    rng = random.Random(seed)
    chosen: list[dict[str, Any]] = []
    for group in sorted(buckets):
        pool = buckets[group]
        take = sample_size_per_value_group
        if take > len(pool):
            raise ValueError(
                f"sample_size_per_value_group={sample_size_per_value_group} needs "
                f"{take} personas for stratum {group!r} but only {len(pool)} available"
            )
        chosen.extend(rng.sample(pool, take))
    rng.shuffle(chosen)
    return chosen


def parse_stratify_field_args(values: list[str]) -> list[str]:
    """Parse repeated or comma-separated ``--stratify`` CLI values."""
    fields: list[str] = []
    for raw in values:
        for part in raw.split(","):
            part = part.strip()
            if part:
                fields.append(part)
    return fields


def sample_personas(
    entries: list[dict[str, Any]], *, sample_size: int, seed: int
) -> list[dict[str, Any]]:
    if sample_size > len(entries):
        raise ValueError(
            f"sample_size={sample_size} exceeds matched pool size={len(entries)}"
        )
    rng = random.Random(seed)
    return rng.sample(entries, sample_size)


def load_persona_yaml(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Persona YAML must be a mapping: {path}")
    return raw


def _persona_dimensions(
    entry: dict[str, Any], *, repo_root: Path
) -> dict[str, Any] | None:
    dims = entry.get("dimensions")
    if isinstance(dims, dict):
        return dims
    path = entry.get("path")
    if not path:
        return None
    raw = load_persona_yaml(repo_root / path)
    dims = raw.get("dimensions")
    return dims if isinstance(dims, dict) else None


def filter_personas_by_confounders(
    entries: list[dict[str, Any]],
    *,
    confounders: dict[str, str],
    repo_root: Path,
) -> list[dict[str, Any]]:
    """Keep personas whose dimensions match all fixed confounder values."""
    if not confounders:
        return list(entries)
    matched: list[dict[str, Any]] = []
    for entry in entries:
        dims = _persona_dimensions(entry, repo_root=repo_root)
        if dims is None:
            continue
        if all(dims.get(key) == value for key, value in confounders.items()):
            matched.append(entry)
    return matched


def sample_personas_probe_stratified(
    entries: list[dict[str, Any]],
    *,
    probe_dimension: str,
    sample_size_per_value_group: int,
    seed: int,
    repo_root: Path,
    probe_values: list[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Sample per probe value group; return chosen entries and synthesis shortages."""
    if sample_size_per_value_group < 1:
        raise ValueError("sample_size_per_value_group must be >= 1")

    probe_key = probe_dimension_key(probe_dimension)
    values = probe_values or values_for_dimension(
        probe_key, catalog_path=str(repo_root / DEFAULT_DIMENSIONS_SCHEMA)
    )
    if not values:
        raise ValueError(f"No catalog values for probe dimension {probe_key!r}")

    buckets: dict[str, list[dict[str, Any]]] = {value: [] for value in values}
    for entry in entries:
        value = get_persona_dimension_value(entry, probe_dimension, repo_root=repo_root)
        if value is None:
            continue
        bucket = buckets.get(str(value))
        if bucket is not None:
            bucket.append(entry)

    rng = random.Random(seed)
    chosen: list[dict[str, Any]] = []
    shortages: dict[str, int] = {}
    for value in values:
        pool = buckets[value]
        need = sample_size_per_value_group
        if len(pool) < need:
            shortages[value] = need - len(pool)
        if pool:
            chosen.extend(rng.sample(pool, min(len(pool), need)))
    rng.shuffle(chosen)
    return chosen, shortages


def _best_template_persona(
    pool: list[dict[str, Any]],
    *,
    confounders: dict[str, str],
    repo_root: Path,
) -> dict[str, Any]:
    """Pick a pool persona to clone when synthesizing missing probe strata."""

    def score(entry: dict[str, Any]) -> int:
        dims = _persona_dimensions(entry, repo_root=repo_root) or {}
        return sum(1 for key, value in confounders.items() if dims.get(key) == value)

    return max(pool, key=score)


def write_reference_cohort_persona(
    *,
    template: dict[str, Any],
    confounders: dict[str, str],
    probe_key: str,
    probe_value: str,
    cohort_dir: Path,
    repo_root: Path,
    suffix: str,
) -> dict[str, Any]:
    """Synthesize a cohort persona with fixed confounders and one probe value."""
    base_id = str(template.get("persona_id", "reference"))
    slug = _slug(probe_value)
    out_id = f"{base_id}-ref-{slug}-{suffix}"
    payload = {
        "persona_id": out_id,
        "version": template.get("version", "1.0"),
        "dimensions": dict(template.get("dimensions") or {}),
    }
    if not isinstance(payload["dimensions"], dict):
        raise ValueError("Template persona missing dimensions block")
    for key, value in confounders.items():
        payload["dimensions"][key] = value
    payload["dimensions"][probe_key] = probe_value

    cohort_dir.mkdir(parents=True, exist_ok=True)
    rel_path = cohort_dir.relative_to(repo_root) / f"persona_{out_id}.yaml"
    out_path = repo_root / rel_path
    out_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return {
        "persona_id": out_id,
        "path": str(rel_path),
        "dimensions": payload["dimensions"],
        "reference_from": base_id,
        "probe_value": probe_value,
        "synthesized": True,
    }


def build_confounder_probe_cohort(
    *,
    repo_root: Path,
    job_slug: str,
    probe_dimension: str,
    confounders: dict[str, str],
    sample_size_per_value_group: int,
    seed: int,
    pool: list[dict[str, Any]],
    grounding: dict[str, object] | None = None,
    probe_values: list[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Filter pool by confounders, stratify on probe only, synthesize gaps."""
    if sample_size_per_value_group < 1:
        raise ValueError("sample_size_per_value_group must be >= 1")

    probe_key = probe_dimension_key(probe_dimension)
    values = probe_values or values_for_dimension(
        probe_key, catalog_path=str(repo_root / DEFAULT_DIMENSIONS_SCHEMA)
    )
    if not values:
        raise ValueError(f"No catalog values for probe dimension {probe_key!r}")

    filtered = filter_personas_by_confounders(
        pool, confounders=confounders, repo_root=repo_root
    )
    chosen, shortages = sample_personas_probe_stratified(
        filtered,
        probe_dimension=probe_dimension,
        sample_size_per_value_group=sample_size_per_value_group,
        seed=seed,
        repo_root=repo_root,
        probe_values=values,
    )

    cohort_dir = repo_root / GENERATED_COHORTS_DIR / job_slug
    if shortages:
        template = load_persona_yaml(
            repo_root
            / _best_template_persona(
                pool, confounders=confounders, repo_root=repo_root
            )["path"]
        )
        synth_index = 0
        for value, missing in shortages.items():
            for _ in range(missing):
                synth_index += 1
                chosen.append(
                    write_reference_cohort_persona(
                        template=template,
                        confounders=confounders,
                        probe_key=probe_key,
                        probe_value=value,
                        cohort_dir=cohort_dir,
                        repo_root=repo_root,
                        suffix=f"s{synth_index}",
                    )
                )
        rng = random.Random(seed + 1)
        rng.shuffle(chosen)

    meta = {
        "controlled_probe": False,
        "confounder_probe": True,
        "confounders": confounders,
        "grounding": grounding or {},
        "filtered_pool_size": len(filtered),
        "probe_values": values,
        "value_group_count": len(values),
        "sample_size_per_value_group": sample_size_per_value_group,
        "synthesized_trials": sum(shortages.values()),
        "cohort_dir": str(cohort_dir.relative_to(repo_root)) if shortages else None,
    }
    return chosen, meta


def write_controlled_cohort_persona(
    *,
    anchor: dict[str, Any],
    probe_key: str,
    probe_value: str,
    cohort_dir: Path,
    repo_root: Path,
) -> dict[str, Any]:
    """Clone anchor persona; only *probe_key* changes."""
    persona_id = str(anchor.get("persona_id", "anchor"))
    slug = _slug(probe_value)
    out_id = f"{persona_id}-probe-{slug}"
    payload = {
        "persona_id": out_id,
        "version": anchor.get("version", "1.0"),
        "dimensions": dict(anchor.get("dimensions") or {}),
    }
    if not isinstance(payload["dimensions"], dict):
        raise ValueError("Anchor persona missing dimensions block")
    payload["dimensions"][probe_key] = probe_value

    cohort_dir.mkdir(parents=True, exist_ok=True)
    rel_path = cohort_dir.relative_to(repo_root) / f"persona_{out_id}.yaml"
    out_path = repo_root / rel_path
    out_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return {
        "persona_id": out_id,
        "path": str(rel_path),
        "dimensions": payload["dimensions"],
        "controlled_from": persona_id,
        "probe_value": probe_value,
    }


def build_controlled_probe_cohort(
    *,
    repo_root: Path,
    job_slug: str,
    probe_dimension: str,
    anchor_persona_path: str,
    sample_size_per_value_group: int,
    seed: int,
    probe_values: list[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Hold all non-probe dimensions at *anchor*; sweep probe values only."""
    if sample_size_per_value_group < 1:
        raise ValueError("sample_size_per_value_group must be >= 1")

    anchor_path = repo_root / anchor_persona_path
    anchor = load_persona_yaml(anchor_path)
    probe_key = probe_dimension_key(probe_dimension)
    values = probe_values or values_for_dimension(
        probe_key, catalog_path=str(repo_root / "persona" / "dimensions.json")
    )
    if not values:
        raise ValueError(f"No catalog values for probe dimension {probe_key!r}")

    cohort_dir = repo_root / GENERATED_COHORTS_DIR / job_slug
    entries = [
        write_controlled_cohort_persona(
            anchor=anchor,
            probe_key=probe_key,
            probe_value=value,
            cohort_dir=cohort_dir,
            repo_root=repo_root,
        )
        for value in values
    ]

    rng = random.Random(seed)
    chosen: list[dict[str, Any]] = []
    for entry in entries:
        chosen.extend([entry] * sample_size_per_value_group)
    rng.shuffle(chosen)

    meta = {
        "controlled_probe": True,
        "anchor_persona_path": anchor_persona_path,
        "anchor_persona_id": anchor.get("persona_id"),
        "probe_values": values,
        "value_group_count": len(values),
        "sample_size_per_value_group": sample_size_per_value_group,
        "cohort_dir": str(cohort_dir.relative_to(repo_root)),
    }
    return chosen, meta


def should_use_confounder_probe(
    *,
    confounders: dict[str, str],
    controlled_probe: bool,
    probe_value: str | None,
    stratify_fields: list[str] | None,
    probe_dimension: str,
) -> bool:
    if controlled_probe or probe_value is not None:
        return False
    if not confounders:
        return False
    if not stratify_fields or len(stratify_fields) != 1:
        return False
    return stratify_fields[0] == probe_dimension


def should_use_controlled_probe(
    *,
    probe_dimension: str,
    stratify_fields: list[str] | None,
    controlled_probe: bool,
    probe_value: str | None,
) -> bool:
    if not controlled_probe or probe_value is not None:
        return False
    if not stratify_fields or len(stratify_fields) != 1:
        return False
    return stratify_fields[0] == probe_dimension


def build_job_config(
    spec: dict[str, Any],
    *,
    repo_root: Path,
    on_progress: Callable[[str, str], None] | None = None,
) -> dict[str, Any]:
    def emit(stage: str, message: str) -> None:
        if on_progress is not None:
            on_progress(stage, message)

    probe = spec["probe"]
    probe_dimension = probe["dimension"]
    probe_value = probe.get("value")
    task_path = spec["task"]
    pool_dir = repo_root / spec["persona_pool"]
    per_value_group = int(spec.get("sample_size_per_value_group", 1))
    sample_size_total = spec.get("sample_size")
    seed = int(spec.get("seed", 42))

    grounding = spec.get("grounding")
    if grounding is None:
        grounding = get_task_grounding_spec(task_path, repo_root=repo_root)
    if grounding and not probe_dimension:
        probe_dimension = probe_dimension_from_grounding(grounding) or probe_dimension

    confounders = dict(spec.get("confounders") or {})
    if not confounders and "confounders" not in spec and grounding:
        confounders = confounder_values_from_grounding(grounding)

    controlled_probe = bool(spec.get("controlled_probe", False))
    anchor_persona = spec.get("anchor_persona", SMOKE_PERSONA_PATH)

    if "stratify_fields" in spec:
        stratify_fields: list[str] | None = spec["stratify_fields"]
    elif probe_value is None:
        stratify_fields = list(DEFAULT_STRATIFY_FIELDS)
    else:
        stratify_fields = None

    emit("load", f"Loading pool {spec['persona_pool']}…")
    pool = load_manifest(pool_dir, repo_root=repo_root)
    emit("load", f"Loaded {len(pool)} personas")
    cohort_meta: dict[str, Any] = {"controlled_probe": False, "confounder_probe": False}
    matched = pool

    if should_use_confounder_probe(
        confounders=confounders,
        controlled_probe=controlled_probe,
        probe_value=str(probe_value) if probe_value is not None else None,
        stratify_fields=stratify_fields,
        probe_dimension=probe_dimension,
    ):
        emit("sample", "Building confounder-probe cohort…")
        job_slug = spec.get("name", "persona-task-grounding-job")
        chosen, cohort_meta = build_confounder_probe_cohort(
            repo_root=repo_root,
            job_slug=job_slug,
            probe_dimension=probe_dimension,
            confounders=confounders,
            sample_size_per_value_group=per_value_group,
            seed=seed,
            pool=pool,
            grounding=grounding,
        )
        matched = filter_personas_by_confounders(
            pool, confounders=confounders, repo_root=repo_root
        )
    elif should_use_controlled_probe(
        probe_dimension=probe_dimension,
        stratify_fields=stratify_fields,
        controlled_probe=controlled_probe,
        probe_value=str(probe_value) if probe_value is not None else None,
    ):
        emit("sample", "Building controlled-probe cohort…")
        job_slug = spec.get("name", "persona-task-grounding-job")
        chosen, cohort_meta = build_controlled_probe_cohort(
            repo_root=repo_root,
            job_slug=job_slug,
            probe_dimension=probe_dimension,
            anchor_persona_path=anchor_persona,
            sample_size_per_value_group=per_value_group,
            seed=seed,
        )
        matched = pool
    elif probe_value is not None:
        emit(
            "sample",
            f"Filtering {probe_dimension}={probe_value} then sampling…",
        )
        matched = filter_personas(
            pool,
            probe_dimension=probe_dimension,
            probe_value=str(probe_value),
            repo_root=repo_root,
        )
        total = int(
            sample_size_total if sample_size_total is not None else per_value_group
        )
        chosen = sample_personas(matched, sample_size=total, seed=seed)
    elif stratify_fields:
        emit(
            "sample",
            f"Stratified sample on {', '.join(stratify_fields)} "
            f"(per cell={per_value_group})…",
        )
        matched = pool
        chosen = sample_personas_stratified(
            pool,
            stratify_fields=stratify_fields,
            sample_size_per_value_group=per_value_group,
            seed=seed,
            repo_root=repo_root,
        )
    else:
        total = int(
            sample_size_total if sample_size_total is not None else per_value_group
        )
        emit("sample", f"Random sample (n={total})…")
        matched = pool
        chosen = sample_personas(matched, sample_size=total, seed=seed)

    sample_size = len(chosen)
    emit("sample", f"Selected {sample_size} trials from {len(matched)} matched")

    agent_spec = spec["agent"]
    job_spec = spec.get("job", {})
    job_slug = spec.get("name", "persona-task-grounding-job")

    agents = [
        {
            "name": agent_spec["name"],
            "model_name": agent_spec["model_name"],
            "kwargs": {"persona_path": entry["path"]},
        }
        for entry in chosen
    ]

    verifier_env: dict[str, str] = {
        "PLAYGROUND_PROBE_DIMENSION": probe_dimension,
        "MATRAIX_PROBE_DIMENSION": probe_dimension,
        **(spec.get("verifier", {}).get("env") or {}),
    }
    if probe_value is not None:
        verifier_env["PLAYGROUND_PROBE_VALUE"] = str(probe_value)
        verifier_env["MATRAIX_PROBE_VALUE"] = str(probe_value)

    return {
        "job_name": job_spec.get("job_name", job_slug),
        "jobs_dir": job_spec.get("jobs_dir", "jobs"),
        "n_attempts": job_spec.get("n_attempts", 1),
        "timeout_multiplier": job_spec.get("timeout_multiplier", 1.0),
        "n_concurrent_trials": job_spec.get("n_concurrent_trials", 1),
        "quiet": job_spec.get("quiet", False),
        "environment": job_spec.get(
            "environment",
            {"type": "docker", "delete": True},
        ),
        "verifier": {"env": verifier_env},
        "agents": agents,
        "tasks": [{"path": spec["task"]}],
        "_job_meta": {
            "job_slug": job_slug,
            "probe": probe,
            "sample_size": sample_size,
            "sample_size_per_value_group": per_value_group,
            "seed": seed,
            "stratify_fields": stratify_fields or [],
            "matched_pool_size": len(matched),
            "selected_persona_ids": [entry["persona_id"] for entry in chosen],
            **cohort_meta,
        },
    }
