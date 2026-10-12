"""Tests for production 1M filter taxonomy catalog."""

from __future__ import annotations

import json

from backend.service.persona_pool_service import PersonaPoolService
from backend.service.persona_taxonomy import build_production_filter_categories
from backend.tests.test_persona_1m_pool import _write_tiny_release


def test_build_production_filter_categories_covers_schema(tmp_path, monkeypatch):
    release = _write_tiny_release(tmp_path, rows=20)
    monkeypatch.setenv("MATRIX_PERSONA_1M_DIR", str(release))
    repo = tmp_path / "repo"
    repo.mkdir()
    cats = build_production_filter_categories(
        repo_root=repo,
        persona_sources=["wiki", "synthetic"],
    )
    assert cats["personaSources"] == ["wiki", "synthetic"]
    assert cats["devProfile"]["dimensionCount"] == 1290  # tiny schema still uses ATTRIBUTE_COUNT
    groups = cats["devProfile"]["groups"]
    assert groups
    assert all(group.get("subgroups") for group in groups)
    dim_ids = {dim["id"] for group in groups for dim in group["dimensions"]}
    assert "age_bracket" in dim_ids
    assert "region" in dim_ids


def test_get_catalog_production_uses_full_taxonomy(tmp_path, monkeypatch):
    release = _write_tiny_release(tmp_path, rows=10)
    monkeypatch.setenv("MATRIX_PERSONA_1M_DIR", str(release))
    repo = tmp_path / "repo"
    (repo / "persona/schema").mkdir(parents=True)
    (repo / "persona/schema/dimension_categories.json").write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "personaSources": ["Nemotron"],
                "devProfile": {
                    "dimensionCount": 1,
                    "groups": [{"id": "demo", "label": "Demo", "dimensionIds": ["age_bracket"]}],
                },
            }
        ),
        encoding="utf-8",
    )
    # Also put a tiny codes schema under release so resolve works via env.
    service = PersonaPoolService(repo_root=repo)
    catalog = service.get_catalog("persona/datasets/matraix-persona-1m")
    assert catalog["kind"] == "production"
    assert "wiki" in catalog["dimensionCategories"]["personaSources"]
    assert "Nemotron" not in catalog["dimensionCategories"]["personaSources"]
    assert catalog["dimensionCategories"]["devProfile"]["dimensionCount"] >= 2
    assert catalog["dimensionCategories"]["devProfile"]["groups"][0].get("subgroups")


def test_get_catalog_bench_uses_full_taxonomy(tmp_path):
    repo = tmp_path
    pool = repo / "persona/datasets/matraix-persona-dev-sample"
    pool.mkdir(parents=True)
    (pool / "manifest.json").write_text(
        json.dumps(
            {
                "count": 1,
                "source_counts": {"Nemotron": 1, "OASIS": 1},
                "personas": [{"persona_id": "0001"}],
            }
        ),
        encoding="utf-8",
    )
    (repo / "persona/schema").mkdir(parents=True)
    (repo / "persona/schema/dimensions.json").write_text(
        json.dumps(
            {
                "schemaVersion": "2.0",
                "dimensions": [
                    {
                        "id": "age_bracket",
                        "label": "Age",
                        "category": "Demographic: Core",
                        "values": ["18-24", "25-34"],
                    },
                    {
                        "id": "region",
                        "label": "Region",
                        "category": "Demographic: Core",
                        "values": ["Europe", "East Asia"],
                    },
                    {
                        "id": "domain",
                        "label": "Domain",
                        "category": "Expertise: Domains",
                        "values": ["Software & AI"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    service = PersonaPoolService(repo_root=repo)
    catalog = service.get_catalog("persona/datasets/matraix-persona-dev-sample")
    assert catalog["dimensionCategories"]["personaSources"] == ["Nemotron", "OASIS"]
    assert catalog["dimensionCategories"]["devProfile"]["dimensionCount"] == 3
    groups = catalog["dimensionCategories"]["devProfile"]["groups"]
    assert groups
    assert any(group.get("subgroups") for group in groups)
    dim_ids = {dim["id"] for group in groups for dim in group["dimensions"]}
    assert dim_ids == {"age_bracket", "region", "domain"}
