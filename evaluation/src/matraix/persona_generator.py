"""Sample synthetic persona YAML from the Full DAG."""

from __future__ import annotations

import itertools
import json
import random
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

import yaml

from matraix.persona_consistency import (
    CONSTRAINED_DIMENSIONS,
    load_dev_dimension_ids,
    load_dev_dimension_index_order,
    allowed_age_brackets_for_life_stage,
    allowed_education,
    allowed_life_stages,
    allowed_seniorities,
    allowed_years_experience,
    validate_dimensions,
)

if TYPE_CHECKING:
    from persona.synthesis.sampler import PersonaForwardSampler

DEFAULT_CATALOG_PATH = "persona/schema/dimensions.json"
DEFAULT_PERSONA_VERSION = "1.0"
SYNTHETIC_SOURCE = "synthetic"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_catalog_values(
    catalog_path: str | Path | None = None,
) -> dict[str, list[str]]:
    path = Path(catalog_path or DEFAULT_CATALOG_PATH)
    if not path.is_file():
        path = _repo_root() / str(catalog_path or DEFAULT_CATALOG_PATH)
    payload = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {}
    for row in payload.get("dimensions") or []:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        dim_id = str(row["id"])
        out[dim_id] = [str(v) for v in row.get("values") or []]
    return out


def _pick(rng, values: list[str]) -> str:
    if not values:
        raise ValueError("empty value list")
    return rng.choice(values)


def _sort_dimensions(
    dimensions: dict[str, str], *, catalog_path: str
) -> dict[str, str]:
    order = load_dev_dimension_index_order(catalog_path=catalog_path)
    return dict(
        sorted(
            dimensions.items(),
            key=lambda item: (order.get(item[0], 99999), item[0]),
        )
    )


def generate_persona_dimensions(
    *,
    rng,
    catalog: dict[str, list[str]],
    dev_dimension_ids: tuple[str, ...],
    catalog_path: str = DEFAULT_CATALOG_PATH,
    age_bracket: str | None = None,
    fixed_dimensions: dict[str, str] | None = None,
) -> dict[str, str]:
    """Sample one internally consistent dimension assignment."""
    fixed = dict(fixed_dimensions or {})
    if fixed.get("age_bracket"):
        age = fixed["age_bracket"]
    elif age_bracket:
        age = age_bracket
    elif fixed.get("life_stage"):
        # Fixed life_stage without age: pick a compatible bracket first so
        # seniority / education lists are never empty (e.g. Student + 65+).
        age = _pick(rng, allowed_age_brackets_for_life_stage(fixed["life_stage"]))
    else:
        age = _pick(rng, catalog["age_bracket"])

    life = fixed.get("life_stage") or _pick(rng, allowed_life_stages(age))
    seniority = fixed.get("seniority") or _pick(
        rng, allowed_seniorities(life_stage=life, age_bracket=age)
    )
    years = fixed.get("years_experience") or _pick(
        rng, allowed_years_experience(age_bracket=age, seniority=seniority)
    )
    education = fixed.get("highest_education") or _pick(
        rng, allowed_education(age_bracket=age, life_stage=life)
    )

    dimensions: dict[str, str] = {
        "age_bracket": age,
        "life_stage": life,
        "seniority": seniority,
        "years_experience": years,
        "highest_education": education,
    }

    for dim_id in dev_dimension_ids:
        if dim_id in CONSTRAINED_DIMENSIONS:
            continue
        if dim_id in fixed:
            dimensions[dim_id] = fixed[dim_id]
            continue
        if dim_id not in catalog:
            raise KeyError(f"Missing dimension {dim_id!r} in catalog")
        dimensions[dim_id] = _pick(rng, catalog[dim_id])

    dimensions = _sort_dimensions(dimensions, catalog_path=catalog_path)

    errors = validate_dimensions(dimensions)
    if errors:
        raise RuntimeError(f"Generated counterfactual persona: {errors}")
    return dimensions


def _stratum_match(dimensions: dict[str, str], stratum: dict[str, str]) -> bool:
    return all(dimensions.get(key) == value for key, value in stratum.items())


def _count_stratum(personas: list[dict[str, Any]], stratum: dict[str, str]) -> int:
    return sum(1 for entry in personas if _stratum_match(entry["dimensions"], stratum))


def _persona_entry(
    *,
    persona_id: str,
    dimensions: dict[str, str],
    version: str,
) -> dict[str, Any]:
    return {
        "persona_id": persona_id,
        "version": version,
        "source": SYNTHETIC_SOURCE,
        "dimensions": dimensions,
    }


def _dag_sampler(*, seed: int) -> PersonaForwardSampler:
    root = str(_repo_root())
    if root not in sys.path:
        sys.path.insert(0, root)
    from persona.synthesis.sampler import DEFAULT_GRAPH_PATH, PersonaForwardSampler, SamplingConfig

    return PersonaForwardSampler(DEFAULT_GRAPH_PATH, SamplingConfig(seed=seed))


def top_up_strata(
    personas: list[dict[str, Any]],
    *,
    strata: list[dict[str, str]],
    min_per_stratum: int,
    persona_version: str = DEFAULT_PERSONA_VERSION,
    sampler: PersonaForwardSampler | None = None,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Add synthetic rows until each filter cell has at least ``min_per_stratum`` matches.

    Filter keys are pinned; every other field is still sampled from the DAG.
    Cells the DAG cannot pin are skipped.
    """
    if min_per_stratum < 1:
        return personas

    out = list(personas)
    next_index = max((int(entry["persona_id"]) for entry in out), default=0) + 1
    dag = sampler or _dag_sampler(seed=seed)

    for stratum in strata:
        if not dag.assignment_supported(stratum):
            continue
        need = min_per_stratum - _count_stratum(out, stratum)
        if need <= 0:
            continue
        for row in dag.sample(need, fixed=stratum):
            out.append(
                _persona_entry(
                    persona_id=str(next_index).zfill(4),
                    dimensions=dict(row),
                    version=persona_version,
                )
            )
            next_index += 1
    return out


def build_probe_strata(
    *,
    confounders: dict[str, str],
    probe_dimension: str,
    probe_values: list[str],
) -> list[dict[str, str]]:
    """One fixed combo per probe value (confounders + probe)."""
    probe_key = probe_dimension.removeprefix("dimensions.")
    return [{**confounders, probe_key: value} for value in probe_values]


def build_filter_strata(
    dimension_filters: dict[str, list[str]],
    *,
    max_strata: int = 2048,
) -> list[dict[str, str]]:
    """Cartesian product of multi-value ``dimensionFilters`` → one cell per combination.

    Pass the result through ``filter_strata_on_dag`` before pinning cells on the
    Full DAG. ``filter_feasible_strata`` is a catalog check for existing pools.
    """
    if not dimension_filters:
        return []

    dims = sorted(
        (
            (
                str(dim).removeprefix("dimensions.").strip(),
                [str(v).strip() for v in values if str(v).strip()],
            )
            for dim, values in dimension_filters.items()
        ),
        key=lambda item: item[0],
    )
    dims = [(dim, values) for dim, values in dims if dim and values]
    if not dims:
        return []

    strata: list[dict[str, str]] = [{}]
    for dim, values in dims:
        next_strata: list[dict[str, str]] = []
        for cell in strata:
            for value in values:
                next_strata.append({**cell, dim: value})
                if len(next_strata) > max_strata:
                    raise ValueError(
                        f"dimensionFilters expand to more than {max_strata} strata; "
                        "narrow filters or raise max_strata"
                    )
        strata = next_strata
    return strata


def filter_feasible_strata(
    strata: list[dict[str, str]],
    *,
    catalog_path: str | Path | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Drop filter cells that combine incompatible constrained dimensions.

    Returns ``(kept, dropped)``.
    """
    cat_path = str(catalog_path or DEFAULT_CATALOG_PATH)
    catalog = load_catalog_values(cat_path)
    dev_ids = load_dev_dimension_ids(catalog_path=cat_path)
    rng = random.Random(0)
    feasible: list[dict[str, str]] = []
    dropped: list[dict[str, str]] = []
    for stratum in strata:
        try:
            generate_persona_dimensions(
                rng=rng,
                catalog=catalog,
                dev_dimension_ids=dev_ids,
                catalog_path=cat_path,
                age_bracket=stratum.get("age_bracket"),
                fixed_dimensions=stratum,
            )
        except (RuntimeError, ValueError):
            dropped.append(stratum)
            continue
        feasible.append(stratum)
    return feasible, dropped


def filter_strata_on_dag(
    strata: list[dict[str, str]],
    *,
    sampler: PersonaForwardSampler | None = None,
    seed: int = 42,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Keep filter cells the Full DAG can pin.

    Drops unknown dimension/value pairs and cells that hit a DAG hard mask.
    Returns ``(kept, dropped)``.
    """
    dag = sampler or _dag_sampler(seed=seed)
    kept: list[dict[str, str]] = []
    dropped: list[dict[str, str]] = []
    for stratum in strata:
        if dag.assignment_supported(stratum):
            kept.append(stratum)
        else:
            dropped.append(stratum)
    return kept, dropped


def stratified_cell_quota(
    *,
    allocation: str | None,
    per_cell: int | None,
    sample_size: int | None,
    n_cells: int,
    default: int = 2,
) -> int:
    """Rows per stratify cell so a later Playground draw will not run short.

    Matches Playground stratified sampling:

    * ``perCell`` — ``N`` in every cell (cohort = ``N × #cells``)
    * ``equalTotal`` — ``ceil(sampleSize / #cells)`` then the draw clips to ``sampleSize``
    * ``proportional`` — same floor so every cell exists and the pool is ≥ ``sampleSize``
    """
    if n_cells < 1:
        raise ValueError("n_cells must be >= 1")
    alloc = str(allocation or "").strip()
    if alloc == "perCell":
        if not isinstance(per_cell, int) or per_cell < 1:
            raise ValueError('allocation "perCell" requires perCell >= 1')
        return per_cell
    if alloc in {"equalTotal", "proportional"}:
        if not isinstance(sample_size, int) or sample_size < 1:
            raise ValueError(f'allocation "{alloc}" requires sampleSize >= 1')
        if alloc == "equalTotal" and sample_size < n_cells:
            raise ValueError(
                f"sampleSize={sample_size} is below the stratified cell count={n_cells} "
                "(need ≥1 persona per combination)"
            )
        return max(1, (sample_size + n_cells - 1) // n_cells)
    if isinstance(per_cell, int) and per_cell >= 1:
        return per_cell
    if isinstance(sample_size, int) and sample_size >= 1:
        return max(1, (sample_size + n_cells - 1) // n_cells)
    return default


def extend_cells_with_allowed_filters(
    cells: list[dict[str, str]],
    extra_filters: dict[str, list[str]],
    *,
    sampler: PersonaForwardSampler,
    max_tries_per_cell: int = 2048,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Pin one allowed value for each extra filter dim so rows survive ``dimensionFilters``."""
    if not extra_filters:
        return list(cells), []
    extra_dims = sorted(extra_filters)
    extra_values = [list(extra_filters[dim]) for dim in extra_dims]
    kept: list[dict[str, str]] = []
    dropped: list[dict[str, str]] = []
    for cell in cells:
        found: dict[str, str] | None = None
        for index, combo in enumerate(itertools.product(*extra_values)):
            if index >= max_tries_per_cell:
                break
            pinned = {**cell, **dict(zip(extra_dims, combo, strict=True))}
            if sampler.assignment_supported(pinned):
                found = pinned
                break
        if found is None:
            dropped.append(cell)
        else:
            kept.append(found)
    return kept, dropped


def strategy_pin_cells(
    *,
    dimension_filters: dict[str, list[str]],
    stratify_fields: list[str] | None = None,
    sampler: PersonaForwardSampler | None = None,
    seed: int = 42,
    max_strata: int = 2048,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Pin cells Playground will bucket on, plus extra filters so rows still match.

    Stratified draws use ``sampling.fields``. Other ``dimensionFilters`` are still
    applied first, so each cell is extended with one allowed value per extra dim.
    """
    dag = sampler or _dag_sampler(seed=seed)
    fields = [
        str(field).removeprefix("dimensions.").strip()
        for field in (stratify_fields or [])
        if str(field).strip()
    ]
    if fields:
        axes = {field: list(dimension_filters[field]) for field in fields}
    else:
        axes = dict(dimension_filters)
    cells = build_filter_strata(axes, max_strata=max_strata)
    cells, dropped = filter_strata_on_dag(cells, sampler=dag)
    extra = {
        key: list(values)
        for key, values in dimension_filters.items()
        if key not in axes
    }
    if extra:
        cells, dropped_extra = extend_cells_with_allowed_filters(
            cells, extra, sampler=dag
        )
        dropped.extend(dropped_extra)
    return cells, dropped


def generate_persona_pool(
    *,
    count: int,
    seed: int = 42,
    smoke_persona_id: str = "0042",
    stratum_top_up: list[dict[str, str]] | None = None,
    min_per_stratum: int = 0,
    persona_version: str = DEFAULT_PERSONA_VERSION,
    include_smoke: bool = True,
) -> list[dict[str, Any]]:
    """Sample ``count`` synthetic personas from the Full DAG.

    ``count`` may be ``0`` to only fill ``stratum_top_up`` cells (each DAG-supported
    cell gets at least ``min_per_stratum`` rows).
    """
    if count < 0:
        raise ValueError("count must be >= 0")
    dag = _dag_sampler(seed=seed)
    personas: list[dict[str, Any]] = []
    for index, row in enumerate(dag.sample(count) if count else [], start=1):
        personas.append(
            _persona_entry(
                persona_id=str(index).zfill(4),
                dimensions=dict(row),
                version=persona_version,
            )
        )

    if stratum_top_up and min_per_stratum > 0:
        kept, _dropped = filter_strata_on_dag(stratum_top_up, sampler=dag)
        personas = top_up_strata(
            personas,
            strata=kept,
            min_per_stratum=min_per_stratum,
            persona_version=persona_version,
            sampler=dag,
            seed=seed,
        )

    if not include_smoke:
        return personas

    if any(entry["persona_id"] == smoke_persona_id for entry in personas):
        return personas
    smoke_entry = _persona_entry(
        persona_id=smoke_persona_id,
        dimensions=dict(dag.sample(1)[0]),
        version=persona_version,
    )
    if not personas:
        return [smoke_entry]
    smoke_index = int(smoke_persona_id) - 1
    if 0 <= smoke_index < len(personas):
        personas[smoke_index] = smoke_entry
        return personas
    personas.append(smoke_entry)
    return personas


def write_persona_dataset(
    *,
    out_dir: Path,
    personas: list[dict[str, Any]],
    repo_root: Path,
    kind: str,
    seed: int,
    smoke_persona_id: str,
    catalog_path: str = DEFAULT_CATALOG_PATH,
    persona_version: str = DEFAULT_PERSONA_VERSION,
    manifest_name: str | None = None,
    manifest_description: str | None = None,
    on_progress: Callable[[str, dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Write one YAML per persona + ``manifest.json``.

    ``on_progress(stage, payload)`` is optional. Stages: ``write`` (with
    ``done``/``total``) and ``manifest``.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    if personas:
        dimension_ids = list(personas[0]["dimensions"])
    else:
        dimension_ids = list(load_dev_dimension_ids(catalog_path=catalog_path))
    manifest_personas: list[dict[str, Any]] = []
    total = len(personas)
    # ~40 updates max so large pools stay responsive without flooding the wire.
    report_every = max(1, total // 40) if total else 1
    for index, entry in enumerate(personas, start=1):
        persona_id = entry["persona_id"]
        rel_path = f"{out_dir.relative_to(repo_root)}/persona_{persona_id}.yaml"
        payload = {
            "persona_id": persona_id,
            "version": entry.get("version", persona_version),
            "source": entry.get("source"),
            "dimensions": entry["dimensions"],
        }
        (repo_root / rel_path).write_text(
            yaml.safe_dump(payload, sort_keys=False), encoding="utf-8"
        )
        manifest_personas.append(
            {
                "persona_id": persona_id,
                "path": rel_path,
                "source": entry.get("source"),
                "dimensions": entry["dimensions"],
            }
        )
        if on_progress and (index == total or index % report_every == 0):
            on_progress(
                "write",
                {
                    "done": index,
                    "total": total,
                    "label": f"Writing personas ({index}/{total})",
                },
            )

    source_counts: dict[str, int] = {}
    for entry in manifest_personas:
        source = entry.get("source")
        if source:
            source_counts[source] = source_counts.get(source, 0) + 1

    if on_progress:
        on_progress("manifest", {"label": "Writing manifest…"})

    manifest: dict[str, Any] = {
        "kind": kind,
        "count": len(manifest_personas),
        "seed": seed,
        "schema_version": persona_version,
        "smoke_persona_id": smoke_persona_id,
        "dimension_ids": list(dimension_ids),
        "dimension_count": len(dimension_ids),
        "dimension_categories": "persona/schema/dimension_categories.json",
        "persona_sources": sorted(source_counts),
        "source_counts": source_counts,
        "personas": manifest_personas,
    }
    if manifest_name:
        manifest["name"] = manifest_name
    if manifest_description:
        manifest["description"] = manifest_description
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest
