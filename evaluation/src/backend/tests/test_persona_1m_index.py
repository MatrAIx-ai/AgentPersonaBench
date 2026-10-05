"""Tests for Persona 1M inverted indexes."""

from __future__ import annotations

import json

from backend.service import persona_1m_index as index_mod
from backend.service import persona_1m_pool as pool_mod
from backend.tests.test_persona_1m_pool import _write_tiny_release


def test_build_and_sample_with_index(tmp_path, monkeypatch):
    release = _write_tiny_release(tmp_path, rows=120)
    monkeypatch.setenv(pool_mod.ENV_1M_DIR, str(release))
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "persona/schema").mkdir(parents=True)
    (repo / "persona/schema/dimension_categories.json").write_text(
        json.dumps({"schemaVersion": "1.0", "personaSources": [], "devProfile": {"groups": []}}),
        encoding="utf-8",
    )

    out = repo / "persona/datasets/matraix-persona-1m/indexes"
    manifest = index_mod.build_indexes(
        repo_root=repo, output_dir=out, progress_every=0
    )
    assert manifest["rows"] == 120
    assert (out / "postings.sqlite").is_file()

    with index_mod.Persona1MIndex.open(out) as index:
        ages = index.values_for_field("age_bracket")
        assert "25-34" in ages
        ids = index.row_ids_for("age_bracket", ["25-34"])
        assert ids.size > 0

    sampled = pool_mod.sample_production_1m(
        repo_root=repo,
        sample_size=4,
        seed=2,
        dimension_filters={"age_bracket": ["18-24", "25-34"]},
        stratify_fields=["age_bracket", "region"],
        sample_size_per_value_group=1,
    )
    assert 1 <= sampled["sampleSize"] <= 4
    assert all(
        card["dimensions"]["age_bracket"] in {"18-24", "25-34"}
        for card in sampled["personas"]
    )


def test_index_source_filter_and_enrich(tmp_path, monkeypatch):
    release = _write_tiny_release(tmp_path, rows=80)
    monkeypatch.setenv(pool_mod.ENV_1M_DIR, str(release))
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "persona/schema").mkdir(parents=True)
    (repo / "persona/schema/dimension_categories.json").write_text(
        json.dumps({"schemaVersion": "1.0", "personaSources": [], "devProfile": {"groups": []}}),
        encoding="utf-8",
    )

    out = repo / "persona/datasets/matraix-persona-1m/indexes"
    manifest = index_mod.build_indexes(
        repo_root=repo, output_dir=out, progress_every=0
    )
    assert manifest.get("sourceIndexed") is True
    assert "wiki" in (manifest.get("sourceValues") or [])

    with index_mod.Persona1MIndex.open(out) as index:
        assert index.has_field("source")
        wiki_ids = index.row_ids_for("source", ["wiki"])
        assert wiki_ids.size > 0
        assert wiki_ids.size == 40  # every other row in the tiny release

    sampled = pool_mod.sample_production_1m(
        repo_root=repo,
        sample_size=5,
        seed=3,
        sources=["wiki"],
        dimension_filters={"age_bracket": ["18-24", "25-34"]},
    )
    assert sampled["sampleSize"] == 5
    assert all(card["source"] == "wiki" for card in sampled["personas"])
    assert all(
        card["dimensions"]["age_bracket"] in {"18-24", "25-34"}
        for card in sampled["personas"]
    )

    # Drop source postings and re-enrich without full rebuild.
    import sqlite3

    conn = sqlite3.connect(out / "postings.sqlite")
    conn.execute("DELETE FROM postings WHERE field_id = ?", ("source",))
    conn.commit()
    conn.close()
    with index_mod.Persona1MIndex.open(out) as index:
        assert not index.has_field("source")

    enriched = index_mod.enrich_source_postings(
        repo_root=repo, index_dir=out, progress_every=0
    )
    assert "wiki" in enriched["sourceValues"]
    with index_mod.Persona1MIndex.open(out) as index:
        assert index.has_field("source")
        assert index.row_ids_for("source", ["synthetic"]).size == 40
