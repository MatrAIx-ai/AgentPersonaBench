"""Production MatrAIx Persona 1M pool — sample from HF Parquet, materialize cohorts.

Cohorts are subsets of the published ``MatrAIx_Persona_1M_Public_Release``
coreset and live under ``persona/datasets/matraix-persona-1m/cohorts/``.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import yaml

from matraix.persona_display_name import assign_cohort_display_names, synthetic_display_name

PRODUCTION_1M_POOL = "persona/datasets/matraix-persona-1m"
PRODUCTION_1M_LABEL = "matraix-persona-1m"
PRODUCTION_1M_KIND = "production"
PRODUCTION_1M_COUNT = 1_000_000
HF_1M_REPO = "MatrAIx2026/MatrAIx_Persona_1M_Public_Release"
ENV_1M_DIR = "MATRIX_PERSONA_1M_DIR"
MAX_SAMPLE_SIZE = 10_000
# Stable random window used for Persona Store 1M browse/search preview paging.
DEFAULT_1M_PREVIEW_WINDOW = 10_000
PERSONA_CARD_DIMENSIONS = (
    "age_bracket",
    "region",
    "domain",
    "intent",
    "life_stage",
    "source",
)

# (release_root, seed, window) → sorted global row indices for deterministic paging.
_preview_index_cache: dict[tuple[str, int, int], list[int]] = {}


def is_production_1m_pool(persona_pool: str | None) -> bool:
    text = (persona_pool or "").strip().rstrip("/")
    return text == PRODUCTION_1M_POOL or text.startswith(f"{PRODUCTION_1M_POOL}/")


def is_production_1m_root(persona_pool: str | None) -> bool:
    return (persona_pool or "").strip().rstrip("/") == PRODUCTION_1M_POOL


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _repo_root() -> Path:
    from playground.harbor.playground import _repo_root as harbor_root

    return harbor_root()


@dataclass(frozen=True)
class Persona1MPaths:
    root: Path
    data_dir: Path
    schema_path: Path
    manifest_path: Path | None

    @property
    def parquet_files(self) -> list[Path]:
        return sorted(self.data_dir.glob("persona-1m-*.parquet"))


def resolve_1m_paths(repo_root: Path | None = None) -> Persona1MPaths:
    """Locate the published 1M coreset on disk (env override or HF cache)."""
    root = Path(repo_root) if repo_root is not None else _repo_root()
    env = os.environ.get(ENV_1M_DIR, "").strip()
    candidates: list[Path] = []
    if env:
        candidates.append(Path(env).expanduser())
    candidates.append(root / PRODUCTION_1M_POOL / "release")
    cached = _hf_cache_snapshot()
    if cached is not None:
        candidates.append(cached)

    for candidate in candidates:
        paths = _paths_from_root(candidate)
        if paths is not None and paths.parquet_files:
            return paths

    raise FileNotFoundError(
        "MatrAIx Persona 1M release not found locally. "
        f"Set {ENV_1M_DIR} to the dataset root (with data/persona-1m-*.parquet), "
        f"or download {HF_1M_REPO} into the Hugging Face cache / "
        f"{PRODUCTION_1M_POOL}/release/."
    )


def _hf_cache_snapshot() -> Path | None:
    try:
        from huggingface_hub import scan_cache_dir
    except ImportError:
        return None
    try:
        cache = scan_cache_dir()
    except Exception:  # noqa: BLE001
        return None
    for info in cache.repos:
        if info.repo_id != HF_1M_REPO or info.repo_type != "dataset":
            continue
        for revision in info.revisions:
            snap = Path(revision.snapshot_path)
            if _paths_from_root(snap) is not None:
                return snap
    return None


def _paths_from_root(root: Path) -> Persona1MPaths | None:
    if not root.is_dir():
        return None
    data_dir = root / "data" if (root / "data").is_dir() else root
    if not list(data_dir.glob("persona-1m-*.parquet")):
        return None
    schema = root / "persona_codes.schema.json"
    if not schema.is_file():
        schema = data_dir / "persona_codes.schema.json"
    if not schema.is_file():
        return None
    manifest = root / "manifest.json"
    return Persona1MPaths(
        root=root,
        data_dir=data_dir,
        schema_path=schema,
        manifest_path=manifest if manifest.is_file() else None,
    )


def production_dataset_entry(*, available: bool) -> dict[str, Any]:
    return {
        "pool": PRODUCTION_1M_POOL,
        "label": PRODUCTION_1M_LABEL,
        "kind": PRODUCTION_1M_KIND,
        "count": PRODUCTION_1M_COUNT if available else 0,
        "default": False,
        "available": available,
    }


def load_codec(schema_path: Path):
    from persona.post_process.unified_dataset.schema import AttributeCodec

    return AttributeCodec.from_codes_schema(schema_path)


def _persona_id(source: str, source_row_index: int) -> str:
    raw = f"{source}:{int(source_row_index)}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    source_slug = re.sub(r"[^a-z0-9]+", "-", (source or "row").lower()).strip("-") or "row"
    return f"{source_slug}-{digest}"


def _decode_batch_rows(batch, codec) -> list[dict[str, Any]]:
    sources = batch.column("source").to_pylist()
    row_indices = batch.column("source_row_index").to_pylist()
    attributes = batch.column("attributes").to_pylist()
    null_bitmaps = batch.column("null_bitmap").to_pylist()
    overrides_col = (
        batch.column("attribute_overrides").to_pylist()
        if "attribute_overrides" in batch.schema.names
        else [None] * len(sources)
    )
    rows: list[dict[str, Any]] = []
    for source, row_index, attrs, null_bitmap, overrides in zip(
        sources, row_indices, attributes, null_bitmaps, overrides_col
    ):
        if attrs is None:
            continue
        dimensions = codec.decode_row(attrs, null_bitmap, overrides)
        source_text = str(source or "unknown")
        persona_id = _persona_id(source_text, int(row_index))
        rows.append(
            {
                "persona_id": persona_id,
                "source": source_text,
                "source_row_index": int(row_index),
                "dimensions": dimensions,
            }
        )
    return rows


def _parquet_row_counts(paths: Persona1MPaths) -> list[tuple[Path, int]]:
    import pyarrow.parquet as pq

    counts: list[tuple[Path, int]] = []
    for parquet_path in paths.parquet_files:
        counts.append((parquet_path, int(pq.ParquetFile(parquet_path).metadata.num_rows)))
    return counts


def _read_decoded_rows_at(
    parquet_path: Path,
    codec,
    row_indices: list[int],
) -> list[dict[str, Any]]:
    """Decode selected global-in-file row indices (sorted)."""
    import pyarrow.parquet as pq

    if not row_indices:
        return []
    wanted = set(row_indices)
    parquet = pq.ParquetFile(parquet_path)
    out: dict[int, dict[str, Any]] = {}
    cursor = 0
    for batch in parquet.iter_batches(
        batch_size=8_192,
        columns=[
            "source",
            "source_row_index",
            "attributes",
            "null_bitmap",
            "attribute_overrides",
        ],
    ):
        batch_len = len(batch)
        start = cursor
        end = cursor + batch_len
        hits = [idx for idx in range(start, end) if idx in wanted]
        if hits:
            local = [idx - start for idx in hits]
            sliced = batch.take(local)
            for file_row, decoded in zip(hits, _decode_batch_rows(sliced, codec)):
                out[file_row] = decoded
            if len(out) == len(wanted):
                break
        cursor = end
    return [out[idx] for idx in row_indices if idx in out]


def _matches_filters(
    row: dict[str, Any],
    *,
    sources: list[str] | None,
    dimension_filters: dict[str, list[str]] | None,
) -> bool:
    if sources:
        wanted = {str(item).strip() for item in sources if str(item).strip()}
        if wanted and str(row.get("source") or "") not in wanted:
            return False
    dims = row.get("dimensions") or {}
    for key, values in (dimension_filters or {}).items():
        if not values:
            continue
        if str(dims.get(key) or "") not in set(values):
            return False
    return True


def _random_sample_unfiltered(
    paths: Persona1MPaths,
    codec,
    *,
    sample_size: int,
    seed: int,
) -> list[dict[str, Any]]:
    """O(sample_size) decode path when there are no source/dimension filters."""
    counts = _parquet_row_counts(paths)
    total = sum(count for _, count in counts)
    if total < 1:
        return []
    take = min(sample_size, total)
    rng = random.Random(seed)
    picked = sorted(rng.sample(range(total), take))

    chosen: list[dict[str, Any]] = []
    offset = 0
    for parquet_path, count in counts:
        local = [idx - offset for idx in picked if offset <= idx < offset + count]
        if local:
            chosen.extend(_read_decoded_rows_at(parquet_path, codec, local))
        offset += count
    return chosen


def _read_decoded_rows_at_global(
    counts: list[tuple[Path, int]],
    codec,
    global_indices: list[int],
) -> list[dict[str, Any]]:
    if not global_indices:
        return []
    by_file: dict[Path, list[int]] = {}
    offset = 0
    wanted = sorted(set(global_indices))
    cursor = 0
    for parquet_path, count in counts:
        local: list[int] = []
        while cursor < len(wanted) and wanted[cursor] < offset + count:
            if wanted[cursor] >= offset:
                local.append(wanted[cursor] - offset)
            cursor += 1
        if local:
            by_file[parquet_path] = local
        offset += count
        if cursor >= len(wanted):
            break
    out: list[dict[str, Any]] = []
    for parquet_path, local in by_file.items():
        out.extend(_read_decoded_rows_at(parquet_path, codec, local))
    return out


def _random_sample_filtered(
    paths: Persona1MPaths,
    codec,
    *,
    sample_size: int,
    seed: int,
    sources: list[str] | None,
    dimension_filters: dict[str, list[str]] | None,
) -> list[dict[str, Any]]:
    """Rejection-sample random row indices until filters fill ``sample_size``.

    Avoids a full Parquet decode scan (reservoir) for small playground samples.
    Falls back to a capped sequential scan only if rejection undersamples.
    """
    counts = _parquet_row_counts(paths)
    total = sum(count for _, count in counts)
    if total < 1:
        return []

    rng = random.Random(seed)
    chosen: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    max_attempts = min(total, max(sample_size * 400, 4_000))
    attempts_left = max_attempts
    while len(chosen) < sample_size and attempts_left > 0:
        batch_n = min(256, attempts_left, max((sample_size - len(chosen)) * 50, 64))
        attempts_left -= batch_n
        probe = sorted({rng.randrange(total) for _ in range(batch_n)})
        for row in _read_decoded_rows_at_global(counts, codec, probe):
            if len(chosen) >= sample_size:
                break
            if not _matches_filters(
                row, sources=sources, dimension_filters=dimension_filters
            ):
                continue
            persona_id = str(row.get("persona_id") or "")
            if not persona_id or persona_id in seen_ids:
                continue
            seen_ids.add(persona_id)
            chosen.append(row)

    if len(chosen) >= sample_size:
        return chosen

    # Rare / selective filters: finish with a sequential pass, stopping early.
    for row in _iter_decoded_rows(paths, codec):
        if len(chosen) >= sample_size:
            break
        if not _matches_filters(row, sources=sources, dimension_filters=dimension_filters):
            continue
        persona_id = str(row.get("persona_id") or "")
        if not persona_id or persona_id in seen_ids:
            continue
        seen_ids.add(persona_id)
        chosen.append(row)
    return chosen


def _iter_decoded_rows(paths: Persona1MPaths, codec) -> Iterator[dict[str, Any]]:
    import pyarrow.parquet as pq

    for parquet_path in paths.parquet_files:
        parquet = pq.ParquetFile(parquet_path)
        for batch in parquet.iter_batches(
            batch_size=4_096,
            columns=[
                "source",
                "source_row_index",
                "attributes",
                "null_bitmap",
                "attribute_overrides",
            ],
        ):
            for row in _decode_batch_rows(batch, codec):
                yield row


def _reservoir_sample(
    rows: Iterator[dict[str, Any]],
    *,
    sample_size: int,
    seed: int,
) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    chosen: list[dict[str, Any]] = []
    seen = 0
    for row in rows:
        seen += 1
        if len(chosen) < sample_size:
            chosen.append(row)
            continue
        replace_at = rng.randrange(seen)
        if replace_at < sample_size:
            chosen[replace_at] = row
    return chosen


def _stratum_key(row: dict[str, Any], fields: list[str]) -> tuple[str, ...] | None:
    dims = row.get("dimensions") or {}
    parts: list[str] = []
    for field in fields:
        value = str(dims.get(field) or "").strip()
        if not value:
            return None
        parts.append(value)
    return tuple(parts)


def _stratified_sample(
    rows: Iterator[dict[str, Any]],
    *,
    sample_size: int,
    seed: int,
    stratify_fields: list[str],
    sample_size_per_value_group: int | None,
) -> list[dict[str, Any]]:
    bare = [str(field).removeprefix("dimensions.").strip() for field in stratify_fields]
    bare = [field for field in bare if field]
    if not bare:
        return _reservoir_sample(rows, sample_size=sample_size, seed=seed)

    per_cell = (
        sample_size_per_value_group
        if isinstance(sample_size_per_value_group, int) and sample_size_per_value_group >= 1
        else None
    )
    buckets: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for row in rows:
        key = _stratum_key(row, bare)
        if key is None:
            continue
        bucket = buckets.setdefault(key, [])
        if per_cell is not None and len(bucket) >= per_cell:
            continue
        bucket.append(row)

    return _flatten_stratum_buckets(
        buckets, sample_size=sample_size, seed=seed, per_cell=per_cell
    )


def _flatten_stratum_buckets(
    buckets: dict[tuple[str, ...], list[dict[str, Any]]],
    *,
    sample_size: int,
    seed: int,
    per_cell: int | None,
) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    chosen: list[dict[str, Any]] = []
    for key in sorted(buckets):
        bucket = list(buckets[key])
        rng.shuffle(bucket)
        if per_cell is not None:
            chosen.extend(bucket[:per_cell])
        else:
            chosen.extend(bucket)

    # Explicit per-cell quota is primary: N per cell across all cells,
    # sample_size is not a clip (mirrors PersonaPoolService contract).
    if per_cell is None and len(chosen) > sample_size:
        rng.shuffle(chosen)
        chosen = chosen[:sample_size]
    return chosen


def _stratified_sample_production(
    paths: Persona1MPaths,
    codec,
    *,
    sample_size: int,
    seed: int,
    stratify_fields: list[str],
    sample_size_per_value_group: int | None,
    sources: list[str] | None,
    dimension_filters: dict[str, list[str]] | None,
    allocation: str | None = None,
) -> list[dict[str, Any]]:
    """Fast stratified sample with sequential early-exit when the target is known."""
    from backend.service.persona_sampling_alloc import sample_proportional_from_buckets

    bare = [str(field).removeprefix("dimensions.").strip() for field in stratify_fields]
    bare = [field for field in bare if field]
    if not bare:
        if sources or dimension_filters:
            return _random_sample_filtered(
                paths,
                codec,
                sample_size=sample_size,
                seed=seed,
                sources=sources,
                dimension_filters=dimension_filters,
            )
        return _random_sample_unfiltered(
            paths, codec, sample_size=sample_size, seed=seed
        )

    allocation_norm = str(allocation or "").strip()
    per_cell = (
        sample_size_per_value_group
        if isinstance(sample_size_per_value_group, int) and sample_size_per_value_group >= 1
        else None
    )
    if allocation_norm == "perCell" and per_cell is None:
        per_cell = 1
    if allocation_norm == "proportional":
        per_cell = None

    buckets: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    seen_ids: set[str] = set()

    def consider(row: dict[str, Any]) -> bool:
        if not _matches_filters(row, sources=sources, dimension_filters=dimension_filters):
            return False
        persona_id = str(row.get("persona_id") or "")
        if not persona_id or persona_id in seen_ids:
            return False
        key = _stratum_key(row, bare)
        if key is None:
            return False
        bucket = buckets.setdefault(key, [])
        if per_cell is not None and len(bucket) >= per_cell:
            return False
        bucket.append(row)
        seen_ids.add(persona_id)
        return True

    # Explicit per-cell: early-exit only when the expected cell count is known
    # (every stratify field constrained by filters) — otherwise a full pass is
    # required, since new cells may appear anywhere in the stream.
    expected_cells: int | None = None
    if per_cell is not None and dimension_filters:
        if all(dimension_filters.get(field) for field in bare):
            expected_cells = 1
            for field in bare:
                expected_cells *= len(dimension_filters[field])

    def done() -> bool:
        if allocation_norm == "proportional":
            return False
        total = sum(len(bucket) for bucket in buckets.values())
        if per_cell is None:
            return total >= sample_size
        if expected_cells is None:
            return False
        return total >= per_cell * expected_cells

    # Single forward pass; stop once the cohort is full.
    for row in _iter_decoded_rows(paths, codec):
        consider(row)
        if done():
            break

    if allocation_norm == "proportional":
        return sample_proportional_from_buckets(
            buckets, sample_size=sample_size, seed=seed
        )

    return _flatten_stratum_buckets(
        buckets, sample_size=sample_size, seed=seed, per_cell=per_cell
    )


def sample_production_1m(
    *,
    repo_root: Path,
    sample_size: int,
    seed: int = 42,
    sources: list[str] | None = None,
    dimension_filters: dict[str, list[str]] | None = None,
    stratify_fields: list[str] | None = None,
    sample_size_per_value_group: int | None = None,
    allocation: str | None = None,
) -> dict[str, Any]:
    if sample_size < 1:
        raise ValueError("sample_size must be >= 1")
    if sample_size > MAX_SAMPLE_SIZE:
        raise ValueError(
            f"sample_size={sample_size} exceeds production max {MAX_SAMPLE_SIZE}. "
            "Sample a cohort from matraix-persona-1m instead of selecting All."
        )

    allocation_norm = str(allocation or "").strip()
    if allocation_norm in {"per_cell", "per-cell"}:
        allocation_norm = "perCell"
    if allocation_norm in {"equal_total", "equal-total"}:
        allocation_norm = "equalTotal"
    if (
        not allocation_norm
        and isinstance(sample_size_per_value_group, int)
        and sample_size_per_value_group >= 1
    ):
        allocation_norm = "perCell"
    if (
        stratify_fields
        and not allocation_norm
        and not (
            isinstance(sample_size_per_value_group, int) and sample_size_per_value_group >= 1
        )
    ):
        allocation_norm = "equalTotal"
    paths = resolve_1m_paths(repo_root)
    codec = load_codec(paths.schema_path)
    has_filters = bool(sources) or bool(dimension_filters)

    # Prefer inverted index for filter / stratified (true random over the match set).
    # Includes ``source`` when the index has source postings; otherwise falls back.
    # Proportional needs full cell populations first — skip the index early-exit path.
    chosen: list[dict[str, Any]] | None = None
    try:
        from backend.service.persona_1m_index import (
            Persona1MIndex,
            resolve_index_dir,
            sample_row_ids_with_index,
        )

        if allocation_norm != "proportional":
            index_dir = resolve_index_dir(repo_root, paths)
            if index_dir is not None:
                with Persona1MIndex.open(index_dir) as index:
                    row_ids = sample_row_ids_with_index(
                        index,
                        sample_size=sample_size,
                        seed=seed,
                        sources=sources,
                        dimension_filters=dimension_filters,
                        stratify_fields=stratify_fields,
                        sample_size_per_value_group=sample_size_per_value_group,
                    )
                if row_ids is not None:
                    if row_ids.size == 0:
                        chosen = []
                    else:
                        counts = _parquet_row_counts(paths)
                        chosen = _read_decoded_rows_at_global(
                            counts, codec, [int(x) for x in row_ids]
                        )
    except Exception:  # noqa: BLE001
        chosen = None

    if chosen is None:
        if stratify_fields:
            chosen = _stratified_sample_production(
                paths,
                codec,
                sample_size=sample_size,
                seed=seed,
                stratify_fields=list(stratify_fields),
                sample_size_per_value_group=sample_size_per_value_group,
                sources=sources,
                dimension_filters=dimension_filters,
                allocation=allocation_norm or None,
            )
        elif has_filters:
            chosen = _random_sample_filtered(
                paths,
                codec,
                sample_size=sample_size,
                seed=seed,
                sources=sources,
                dimension_filters=dimension_filters,
            )
        else:
            chosen = _random_sample_unfiltered(
                paths, codec, sample_size=sample_size, seed=seed
            )

    if not chosen:
        raise ValueError("No personas matched filters in MatrAIx Persona 1M")
    if len(chosen) < sample_size and not stratify_fields:
        raise ValueError(
            f"Requested sample_size={sample_size} but only matched {len(chosen)} personas"
        )

    cohort = materialize_cohort(
        repo_root=repo_root,
        rows=chosen,
        seed=seed,
        sample_size=sample_size,
        sources=sources,
        dimension_filters=dimension_filters,
        stratify_fields=stratify_fields,
        sample_size_per_value_group=sample_size_per_value_group,
    )
    return {
        "pool": cohort["pool"],
        "matchedCount": len(chosen),
        "sampleSize": len(cohort["personaIds"]),
        "seed": seed,
        "personaIds": cohort["personaIds"],
        "personas": cohort["personas"],
        "fields": list(stratify_fields or []),
        "productionSource": HF_1M_REPO,
    }


def materialize_cohort(
    *,
    repo_root: Path,
    rows: list[dict[str, Any]],
    seed: int,
    sample_size: int,
    sources: list[str] | None = None,
    dimension_filters: dict[str, list[str]] | None = None,
    stratify_fields: list[str] | None = None,
    sample_size_per_value_group: int | None = None,
) -> dict[str, Any]:
    digest = hashlib.sha1(
        json.dumps(
            {
                "seed": seed,
                "sample_size": sample_size,
                "sources": sources or [],
                "filters": dimension_filters or {},
                "stratify": stratify_fields or [],
                "per_cell": sample_size_per_value_group,
                "ids": [row["persona_id"] for row in rows],
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:12]
    rel_pool = f"{PRODUCTION_1M_POOL}/cohorts/cohort-{digest}"
    out_dir = repo_root / rel_pool
    out_dir.mkdir(parents=True, exist_ok=True)

    display_names = assign_cohort_display_names(
        [(str(row["persona_id"]), dict(row.get("dimensions") or {})) for row in rows]
    )

    manifest_personas: list[dict[str, Any]] = []
    source_counts: dict[str, int] = {}
    for row in rows:
        persona_id = str(row["persona_id"])
        source = str(row.get("source") or "unknown")
        dimensions = {
            str(key): str(value)
            for key, value in dict(row.get("dimensions") or {}).items()
            if value is not None and str(value).strip()
        }
        rel_yaml = f"{rel_pool}/persona_{persona_id}.yaml"
        payload = {
            "persona_id": persona_id,
            "version": "1.0",
            "source": source,
            "display_name": display_names.get(persona_id),
            "dimensions": dimensions,
        }
        (repo_root / rel_yaml).write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=False),
            encoding="utf-8",
        )
        card_dims = {
            key: dimensions[key]
            for key in PERSONA_CARD_DIMENSIONS
            if key != "source" and key in dimensions
        }
        manifest_personas.append(
            {
                "persona_id": persona_id,
                "display_name": display_names.get(persona_id),
                "path": rel_yaml,
                "source": source,
                "dimensions": card_dims,
            }
        )
        source_counts[source] = source_counts.get(source, 0) + 1

    manifest = {
        "kind": "matraix-persona-1m-cohort",
        "parent_pool": PRODUCTION_1M_POOL,
        "hf_repo": HF_1M_REPO,
        "count": len(manifest_personas),
        "seed": seed,
        "schema_version": "1.0",
        "smoke_persona_id": manifest_personas[0]["persona_id"] if manifest_personas else None,
        "source_counts": source_counts,
        "dimension_categories": "persona/schema/dimension_categories.json",
        "created_at": _utc_now(),
        "personas": manifest_personas,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    persona_ids = [item["persona_id"] for item in manifest_personas]
    cards = [
        {
            "personaId": item["persona_id"],
            "name": item.get("display_name") or f"persona-{item['persona_id']}",
            "source": item.get("source"),
            "path": item.get("path"),
            "dimensions": dict(item.get("dimensions") or {}),
        }
        for item in manifest_personas
    ]
    return {
        "pool": rel_pool,
        "count": len(persona_ids),
        "personaIds": persona_ids,
        "personas": cards,
        "seed": seed,
        "sources": sources or [],
        "dimensionFilters": dimension_filters or {},
        "fields": stratify_fields or [],
        "productionSource": HF_1M_REPO,
    }


def clear_preview_index_cache() -> None:
    """Test helper — drop cached 1M preview index windows."""
    _preview_index_cache.clear()


def _preview_global_indices(
    paths: Persona1MPaths,
    *,
    window: int,
    seed: int,
) -> list[int]:
    """Return a stable sorted sample of global row ids for preview paging."""
    take = max(1, int(window))
    key = (str(paths.root.resolve()), int(seed), take)
    cached = _preview_index_cache.get(key)
    if cached is not None:
        return cached
    counts = _parquet_row_counts(paths)
    total = sum(count for _, count in counts)
    if total < 1:
        _preview_index_cache[key] = []
        return []
    rng = random.Random(seed)
    picked = sorted(rng.sample(range(total), min(take, total)))
    _preview_index_cache[key] = picked
    return picked


def preview_production_1m(
    *,
    repo_root: Path,
    limit: int = 8,
    offset: int = 0,
    seed: int = 42,
    window: int | None = None,
) -> dict[str, Any]:
    """Decode a page from a deterministic 1M preview window.

    Indices for ``window`` (default 10k) are sampled once per ``(release, seed,
    window)`` and cached so ``offset`` pages stay consistent without re-picking.
    """
    paths = resolve_1m_paths(repo_root)
    codec = load_codec(paths.schema_path)
    start = max(0, int(offset))
    page_size = max(1, int(limit))
    end = start + page_size
    win = max(int(window) if window is not None else DEFAULT_1M_PREVIEW_WINDOW, end)
    indices = _preview_global_indices(paths, window=win, seed=seed)
    page_indices = indices[start:end]
    counts = _parquet_row_counts(paths)
    rows = _read_decoded_rows_at_global(counts, codec, page_indices)
    cards = []
    for row in rows:
        dims_full = {
            str(key): str(value)
            for key, value in (row.get("dimensions") or {}).items()
            if value is not None and str(value).strip()
        }
        display = {
            key: dims_full[key]
            for key in PERSONA_CARD_DIMENSIONS
            if key != "source" and dims_full.get(key)
        }
        persona_id = str(row["persona_id"])
        source = str(row.get("source") or "")
        name = synthetic_display_name(persona_id, dims_full)
        search_parts = [persona_id, name, source]
        for key, value in dims_full.items():
            search_parts.append(str(key))
            search_parts.append(str(value))
        cards.append(
            {
                "personaId": persona_id,
                "name": name,
                "source": source or None,
                "path": None,
                "dimensions": display,
                "searchText": " ".join(search_parts),
            }
        )
    return {
        "pool": PRODUCTION_1M_POOL,
        "personas": cards,
        "count": PRODUCTION_1M_COUNT,
        "offset": start,
        "limit": page_size,
        "previewCount": len(indices),
    }


def production_1m_available(repo_root: Path | None = None) -> bool:
    try:
        resolve_1m_paths(repo_root)
        return True
    except FileNotFoundError:
        return False


def _detail_payload_from_row(
    *,
    row: dict[str, Any],
    pool: str,
    path: str = "",
    yaml_text: str = "",
    repo_root: Path | None = None,
) -> dict[str, Any]:
    from backend.service.persona_taxonomy import build_dimension_groups

    persona_id = str(row["persona_id"])
    source = str(row.get("source") or "unknown")
    dimensions = {
        str(key): str(value)
        for key, value in dict(row.get("dimensions") or {}).items()
        if value is not None and str(value).strip()
    }
    if not yaml_text and dimensions:
        yaml_text = yaml.safe_dump(
            {
                "persona_id": persona_id,
                "version": "1.0",
                "source": source,
                "dimensions": dimensions,
            },
            sort_keys=False,
            allow_unicode=False,
        )
    profile_markdown_lines = [
        f"**Persona ID:** `{persona_id}`",
        f"**Source:** {source}",
    ]
    if path:
        profile_markdown_lines.append(f"**Path:** `{path}`")
    if yaml_text.strip():
        profile_markdown_lines.extend(["", "```yaml", yaml_text.rstrip(), "```"])
    display_name = str(row.get("display_name") or "").strip() or synthetic_display_name(
        persona_id, dimensions
    )
    return {
        "personaId": persona_id,
        "name": display_name,
        "source": source,
        "path": path or None,
        "dimensions": dimensions,
        "dimensionGroups": build_dimension_groups(dimensions, repo_root=repo_root),
        "pool": pool,
        "yaml": yaml_text,
        "profileMarkdown": "\n".join(profile_markdown_lines),
    }


def _find_row_by_persona_id(
    paths: Persona1MPaths,
    codec,
    persona_id: str,
) -> dict[str, Any] | None:
    """Locate one persona by id using cheap source/index matching, then decode."""
    found = _find_rows_by_persona_ids(paths, codec, [persona_id])
    return found.get(persona_id.strip())


def _find_rows_by_persona_ids(
    paths: Persona1MPaths,
    codec,
    persona_ids: list[str],
) -> dict[str, dict[str, Any]]:
    """Locate many personas by id in a single Parquet pass."""
    import pyarrow.parquet as pq

    wanted = {pid.strip() for pid in persona_ids if isinstance(pid, str) and pid.strip()}
    if not wanted:
        return {}
    found: dict[str, dict[str, Any]] = {}
    for parquet_path in paths.parquet_files:
        parquet = pq.ParquetFile(parquet_path)
        cursor = 0
        for batch in parquet.iter_batches(
            batch_size=8_192,
            columns=["source", "source_row_index"],
        ):
            sources = batch.column("source").to_pylist()
            row_indices = batch.column("source_row_index").to_pylist()
            hits: list[tuple[str, int]] = []
            for local_idx, (source, row_index) in enumerate(zip(sources, row_indices)):
                persona_id = _persona_id(str(source or "unknown"), int(row_index))
                if persona_id in wanted and persona_id not in found:
                    hits.append((persona_id, cursor + local_idx))
            if hits:
                decoded = _read_decoded_rows_at(
                    parquet_path, codec, [offset for _, offset in hits]
                )
                for (persona_id, _), row in zip(hits, decoded):
                    found[persona_id] = row
                if len(found) >= len(wanted):
                    return found
            cursor += len(batch)
    return found


def _row_from_cohort_yaml(yaml_path: Path, *, persona_id: str) -> dict[str, Any] | None:
    try:
        payload = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(payload, dict):
        return None
    return {
        "persona_id": str(payload.get("persona_id") or persona_id),
        "source": payload.get("source") or "unknown",
        "dimensions": payload.get("dimensions") or {},
    }


def materialize_production_1m_persona_ids(
    *,
    repo_root: Path,
    persona_ids: list[str],
    seed: int = 42,
) -> dict[str, Any]:
    """Materialize an explicit 1M persona-id selection into a local cohort.

    Playground can preview ids from the HF/Parquet index without on-disk YAML.
    Harbor launch needs YAML under a cohort pool — this bridges the gap for
    hand-picked single (or few) personas from ``matraix-persona-1m``.
    """
    ordered_ids: list[str] = []
    seen: set[str] = set()
    for raw in persona_ids:
        pid = str(raw or "").strip()
        if not pid or pid in seen:
            continue
        seen.add(pid)
        ordered_ids.append(pid)
    if not ordered_ids:
        raise ValueError("persona_ids must not be empty")

    rows_by_id: dict[str, dict[str, Any]] = {}
    missing = list(ordered_ids)

    # Prefer already-materialized cohort YAMLs (exact launch artifacts).
    cohorts_root = repo_root / PRODUCTION_1M_POOL / "cohorts"
    if cohorts_root.is_dir():
        still_missing: list[str] = []
        for pid in missing:
            hit: dict[str, Any] | None = None
            for cohort_dir in sorted(cohorts_root.iterdir()):
                if not cohort_dir.is_dir():
                    continue
                yaml_path = cohort_dir / f"persona_{pid}.yaml"
                if not yaml_path.is_file():
                    continue
                hit = _row_from_cohort_yaml(yaml_path, persona_id=pid)
                if hit is not None:
                    break
            if hit is None:
                still_missing.append(pid)
            else:
                rows_by_id[pid] = hit
        missing = still_missing

    if missing:
        paths = resolve_1m_paths(repo_root)
        codec = load_codec(paths.schema_path)
        found = _find_rows_by_persona_ids(paths, codec, missing)
        rows_by_id.update(found)
        missing = [pid for pid in missing if pid not in found]

    if missing:
        raise ValueError(
            "unknown persona in matraix-persona-1m: {}".format(", ".join(missing))
        )

    rows = [rows_by_id[pid] for pid in ordered_ids]
    cohort = materialize_cohort(
        repo_root=repo_root,
        rows=rows,
        seed=seed,
        sample_size=len(rows),
    )
    return {
        "pool": cohort["pool"],
        "matchedCount": len(rows),
        "sampleSize": len(cohort["personaIds"]),
        "seed": seed,
        "personaIds": cohort["personaIds"],
        "personas": cohort["personas"],
        "fields": [],
        "productionSource": HF_1M_REPO,
    }


def get_production_1m_persona_detail(
    *,
    repo_root: Path,
    persona_id: str,
    persona_pool: str = PRODUCTION_1M_POOL,
) -> dict[str, Any]:
    """Resolve a production 1M persona for the detail panel.

    Order: materialized cohort YAML → Parquet lookup by id.
    """
    pid = persona_id.strip()
    if not pid:
        raise FileNotFoundError("persona not found: empty id")

    # Prefer an already-materialized cohort YAML (exact launch artifact).
    cohorts_root = repo_root / PRODUCTION_1M_POOL / "cohorts"
    if cohorts_root.is_dir():
        for cohort_dir in sorted(cohorts_root.iterdir()):
            if not cohort_dir.is_dir():
                continue
            yaml_path = cohort_dir / f"persona_{pid}.yaml"
            if not yaml_path.is_file():
                continue
            payload = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            rel = f"{PRODUCTION_1M_POOL}/cohorts/{cohort_dir.name}/persona_{pid}.yaml"
            return _detail_payload_from_row(
                row={
                    "persona_id": str(payload.get("persona_id") or pid),
                    "source": payload.get("source") or "unknown",
                    "display_name": payload.get("display_name") or "",
                    "dimensions": payload.get("dimensions") or {},
                },
                pool=f"{PRODUCTION_1M_POOL}/cohorts/{cohort_dir.name}",
                path=rel,
                yaml_text=yaml_path.read_text(encoding="utf-8"),
                repo_root=repo_root,
            )

    paths = resolve_1m_paths(repo_root)
    codec = load_codec(paths.schema_path)
    row = _find_row_by_persona_id(paths, codec, pid)
    if row is None:
        raise FileNotFoundError(f"persona not found in matraix-persona-1m: {pid}")
    return _detail_payload_from_row(
        row=row,
        pool=persona_pool or PRODUCTION_1M_POOL,
        repo_root=repo_root,
    )
