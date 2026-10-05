"""Tests for production MatrAIx Persona 1M sampling / materialization."""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from backend.service import persona_1m_pool as pool_mod
from backend.service.persona_pool_service import PersonaPoolService
from persona.post_process.unified_dataset.schema import (
    ATTRIBUTE_BYTES,
    ATTRIBUTE_COUNT,
    AttributeCodec,
    UNIFIED_SCHEMA,
)


def _tiny_schema(path: Path) -> AttributeCodec:
    payload = {
        "format": "persona_codes",
        "format_version": 1,
        "columns": [
            {
                "id": f"dim_{index:04d}",
                "label": f"Dim {index}",
                "category": "test",
                "values": [f"v{index}-a", f"v{index}-b", f"v{index}-c"],
            }
            for index in range(ATTRIBUTE_COUNT)
        ],
    }
    # Keep a few real playbook dims for filter/stratify tests.
    payload["columns"][0] = {
        "id": "age_bracket",
        "label": "Age",
        "category": "Demographic: Core",
        "values": ["18-24", "25-34", "35-44", "45-54"],
    }
    payload["columns"][1] = {
        "id": "region",
        "label": "Region",
        "category": "Demographic: Core",
        "values": ["North America", "Europe", "East Asia", "South Asia"],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return AttributeCodec.from_codes_schema(path)


def _write_tiny_release(root: Path, *, rows: int = 40) -> Path:
    release = root / "release"
    data = release / "data"
    data.mkdir(parents=True)
    codec = _tiny_schema(release / "persona_codes.schema.json")
    sources = []
    source_rows = []
    attributes = []
    null_bitmaps = []
    for i in range(rows):
        dims = {
            "age_bracket": ["18-24", "25-34", "35-44", "45-54"][i % 4],
            "region": ["North America", "Europe", "East Asia", "South Asia"][i % 4],
        }
        packed, nulls, _overrides = codec.encode_mapping(dims)
        sources.append("synthetic" if i % 2 else "wiki")
        source_rows.append(i)
        attributes.append(packed)
        null_bitmaps.append(nulls)
    table = pa.table(
        {
            "source": pa.array(sources, type=pa.string()),
            "source_row_index": pa.array(source_rows, type=pa.uint64()),
            "source_record_id": pa.array([None] * rows, type=pa.string()),
            "attributes": pa.array(attributes, type=pa.binary(ATTRIBUTE_BYTES)),
            "null_bitmap": pa.array(null_bitmaps, type=pa.binary((ATTRIBUTE_COUNT + 7) // 8)),
            "attribute_overrides": pa.array([None] * rows, type=UNIFIED_SCHEMA.field("attribute_overrides").type),
            "has_description": pa.array([False] * rows),
            "descriptions": pa.array([None] * rows, type=UNIFIED_SCHEMA.field("descriptions").type),
            "grounding": pa.array([None] * rows, type=UNIFIED_SCHEMA.field("grounding").type),
            "metadata_json": pa.array([None] * rows, type=pa.string()),
        },
        schema=UNIFIED_SCHEMA,
    )
    pq.write_table(table, data / "persona-1m-0000.parquet")
    (release / "manifest.json").write_text(
        json.dumps({"format": "matraix_persona_1m_coreset", "rows": rows}),
        encoding="utf-8",
    )
    return release


def test_attribute_codec_roundtrip(tmp_path):
    schema = tmp_path / "persona_codes.schema.json"
    codec = _tiny_schema(schema)
    values = {"age_bracket": "25-34", "region": "East Asia"}
    packed, nulls, overrides = codec.encode_mapping(values)
    decoded = codec.decode_row(packed, nulls, overrides)
    assert decoded["age_bracket"] == "25-34"
    assert decoded["region"] == "East Asia"


def test_filtered_sample_is_fast_enough(tmp_path, monkeypatch):
    release = _write_tiny_release(tmp_path, rows=200)
    monkeypatch.setenv(pool_mod.ENV_1M_DIR, str(release))
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "persona/schema").mkdir(parents=True)
    (repo / "persona/schema/dimension_categories.json").write_text(
        json.dumps({"schemaVersion": "1.0", "personaSources": [], "devProfile": {"groups": []}}),
        encoding="utf-8",
    )
    result = pool_mod.sample_production_1m(
        repo_root=repo,
        sample_size=4,
        seed=3,
        dimension_filters={"age_bracket": ["18-24", "25-34"]},
    )
    assert result["sampleSize"] == 4
    assert all(card["dimensions"]["age_bracket"] in {"18-24", "25-34"} for card in result["personas"])


def test_stratified_sample_respects_per_cell(tmp_path, monkeypatch):
    release = _write_tiny_release(tmp_path, rows=200)
    monkeypatch.setenv(pool_mod.ENV_1M_DIR, str(release))
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "persona/schema").mkdir(parents=True)
    (repo / "persona/schema/dimension_categories.json").write_text(
        json.dumps({"schemaVersion": "1.0", "personaSources": [], "devProfile": {"groups": []}}),
        encoding="utf-8",
    )
    result = pool_mod.sample_production_1m(
        repo_root=repo,
        sample_size=8,
        seed=5,
        stratify_fields=["age_bracket", "region"],
        sample_size_per_value_group=1,
    )
    assert 1 <= result["sampleSize"] <= 8
    keys = {
        (card["dimensions"]["age_bracket"], card["dimensions"]["region"])
        for card in result["personas"]
    }
    assert len(keys) == result["sampleSize"]


def test_sample_production_1m_materializes_cohort(tmp_path, monkeypatch):
    release = _write_tiny_release(tmp_path)
    monkeypatch.setenv(pool_mod.ENV_1M_DIR, str(release))
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "persona/schema").mkdir(parents=True)
    (repo / "persona/schema/dimension_categories.json").write_text(
        json.dumps({"schemaVersion": "1.0", "personaSources": [], "devProfile": {"groups": []}}),
        encoding="utf-8",
    )

    result = pool_mod.sample_production_1m(
        repo_root=repo,
        sample_size=8,
        seed=7,
        sources=["wiki"],
    )
    assert result["sampleSize"] == 8
    assert result["pool"].startswith("persona/datasets/matraix-persona-1m/cohorts/")
    out = repo / result["pool"]
    assert (out / "manifest.json").is_file()
    assert len(list(out.glob("persona_*.yaml"))) == 8
    assert all(card["source"] == "wiki" for card in result["personas"])


def test_materialize_production_1m_persona_ids(tmp_path, monkeypatch):
    release = _write_tiny_release(tmp_path)
    monkeypatch.setenv(pool_mod.ENV_1M_DIR, str(release))
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "persona/schema").mkdir(parents=True)
    (repo / "persona/schema/dimension_categories.json").write_text(
        json.dumps({"schemaVersion": "1.0", "personaSources": [], "devProfile": {"groups": []}}),
        encoding="utf-8",
    )

    preview = pool_mod.sample_production_1m(
        repo_root=repo,
        sample_size=3,
        seed=11,
        sources=["wiki"],
    )
    target_ids = preview["personaIds"][:2]

    # Drop the sampled cohort so lookup must go through Parquet.
    import shutil

    shutil.rmtree(repo / preview["pool"])

    result = pool_mod.materialize_production_1m_persona_ids(
        repo_root=repo,
        persona_ids=target_ids,
        seed=11,
    )
    assert result["personaIds"] == target_ids
    assert result["pool"].startswith("persona/datasets/matraix-persona-1m/cohorts/")
    out = repo / result["pool"]
    assert (out / "manifest.json").is_file()
    for persona_id in target_ids:
        assert (out / f"persona_{persona_id}.yaml").is_file()


def test_materialize_production_1m_persona_ids_unknown(tmp_path, monkeypatch):
    release = _write_tiny_release(tmp_path)
    monkeypatch.setenv(pool_mod.ENV_1M_DIR, str(release))
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(ValueError, match="unknown persona"):
        pool_mod.materialize_production_1m_persona_ids(
            repo_root=repo,
            persona_ids=["wiki-does-not-exist"],
            seed=1,
        )


def test_persona_pool_service_samples_production_1m(tmp_path, monkeypatch):
    release = _write_tiny_release(tmp_path)
    monkeypatch.setenv(pool_mod.ENV_1M_DIR, str(release))
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "persona/schema").mkdir(parents=True)
    (repo / "persona/schema/dimension_categories.json").write_text(
        json.dumps({"schemaVersion": "1.0", "personaSources": [], "devProfile": {"groups": []}}),
        encoding="utf-8",
    )
    service = PersonaPoolService(repo_root=repo)
    sampled = service.sample_pool(
        persona_pool=pool_mod.PRODUCTION_1M_POOL,
        sample_size=5,
        seed=3,
    )
    assert sampled["sampleSize"] == 5
    assert "matraix-persona-1m/cohorts/" in sampled["pool"]

    detail = service.get_persona_detail(
        sampled["personaIds"][0],
        persona_pool=pool_mod.PRODUCTION_1M_POOL,
    )
    assert detail["personaId"] == sampled["personaIds"][0]
    assert detail["profileMarkdown"]
    assert detail["dimensions"]
    assert detail["dimensionGroups"]
    assert sum(int(group["count"]) for group in detail["dimensionGroups"]) >= 1

    with pytest.raises(ValueError, match="All is not supported"):
        service.list_persona_ids(pool_mod.PRODUCTION_1M_POOL)


def test_preview_production_1m_pages_are_stable(tmp_path, monkeypatch):
    release = _write_tiny_release(tmp_path, rows=80)
    monkeypatch.setenv(pool_mod.ENV_1M_DIR, str(release))
    repo = tmp_path / "repo"
    repo.mkdir()
    pool_mod.clear_preview_index_cache()

    page0 = pool_mod.preview_production_1m(
        repo_root=repo, limit=10, offset=0, seed=11, window=40
    )
    page1 = pool_mod.preview_production_1m(
        repo_root=repo, limit=10, offset=10, seed=11, window=40
    )
    full = pool_mod.preview_production_1m(
        repo_root=repo, limit=20, offset=0, seed=11, window=40
    )

    ids0 = [card["personaId"] for card in page0["personas"]]
    ids1 = [card["personaId"] for card in page1["personas"]]
    ids_full = [card["personaId"] for card in full["personas"]]
    assert len(ids0) == 10
    assert len(ids1) == 10
    assert ids0 + ids1 == ids_full
    assert page0["previewCount"] == 40
    assert set(ids0).isdisjoint(ids1)

    again = pool_mod.preview_production_1m(
        repo_root=repo, limit=10, offset=0, seed=11, window=40
    )
    assert [card["personaId"] for card in again["personas"]] == ids0

