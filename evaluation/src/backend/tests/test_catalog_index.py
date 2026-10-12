"""Tests for :class:`backend.service.catalog_index.CatalogIndex`.

Covers loading (with junk-line tolerance), id lookup, substring + genre search,
limits / browse mode, counting, and graceful degradation on a missing / ``None``
catalog path.
"""

from __future__ import annotations

import os

from backend.service.catalog_index import CatalogIndex


def test_loads_only_valid_items(catalog):
    """Blank, malformed, and no-id lines are skipped; valid rows are indexed."""
    assert catalog.available is True
    # 4 valid rows in the fixture; 3 junk lines must be ignored.
    assert catalog.size == 4
    assert len(catalog) == 4


def test_get_and_title_for(catalog):
    item = catalog.get("cmu:2")
    assert item is not None
    assert item["title"] == "Casablanca"
    assert catalog.title_for("cmu:2") == "Casablanca"


def test_get_unknown_returns_none(catalog):
    assert catalog.get("does-not-exist") is None
    assert catalog.get("") is None
    assert catalog.title_for("does-not-exist") is None


def test_search_substring_case_insensitive(catalog):
    # 'blade' appears in the Blade Runner title/description.
    ids = [it["item_id"] for it in catalog.search("BLADE")]
    assert ids == ["cmu:1"]
    # Match against description text too.
    ids = [it["item_id"] for it in catalog.search("detective")]
    assert "cmu:3" in ids


def test_search_matches_categories(catalog):
    # 'noir' is only in categories (Film-noir) for cmu:1 and cmu:3.
    ids = {it["item_id"] for it in catalog.search("noir")}
    assert ids == {"cmu:1", "cmu:3"}


def test_search_genre_filter(catalog):
    ids = {it["item_id"] for it in catalog.search("", genre="sci-fi")}
    assert ids == {"cmu:1", "cmu:4"}


def test_search_query_and_genre_combined(catalog):
    # Query 'a' is broad; genre narrows to horror -> only Alien (cmu:4).
    ids = [it["item_id"] for it in catalog.search("alien", genre="horror")]
    assert ids == ["cmu:4"]


def test_search_empty_query_browses_all(catalog):
    ids = [it["item_id"] for it in catalog.search("", limit=0)]
    # limit<=0 disables the cap; order is stable catalog order.
    assert ids == ["cmu:1", "cmu:2", "cmu:3", "cmu:4"]


def test_search_respects_limit(catalog):
    results = catalog.search("", limit=2)
    assert len(results) == 2
    assert [it["item_id"] for it in results] == ["cmu:1", "cmu:2"]


def test_search_no_match_returns_empty(catalog):
    assert catalog.search("zzzz-not-a-word") == []


def test_count_ignores_limit(catalog):
    # count reports the full match total regardless of any search limit.
    assert catalog.count("") == 4
    assert catalog.count("noir") == 2
    assert catalog.count("", genre="sci-fi") == 2
    assert catalog.count("zzzz") == 0


def test_missing_file_is_tolerated(tmp_path):
    missing = os.path.join(str(tmp_path), "nope.jsonl")
    idx = CatalogIndex(missing)
    assert idx.available is False
    assert idx.size == 0
    assert idx.search("anything") == []
    assert idx.count("anything") == 0
    assert idx.get("cmu:1") is None


def test_none_path_is_tolerated():
    idx = CatalogIndex(None)
    assert idx.available is False
    assert idx.size == 0
    assert idx.catalog_path is None


def test_catalog_path_attribute_is_set(catalog, catalog_path):
    assert catalog.catalog_path == catalog_path


def test_from_items_builds_searchable_index():
    """``from_items`` builds a ready index from normalized dicts (no file).

    This is the constructor the real-bundle catalog uses: rows already shaped
    like normalized items (``item_id`` / ``title`` / ``categories``) are indexed
    in order and become searchable without touching disk.
    """
    items = [
        {"item_id": "1", "title": "Toy Story", "categories": ["Animation", "Children"]},
        {"item_id": "2", "title": "Jumanji", "categories": ["Adventure", "Children"]},
    ]
    index = CatalogIndex.from_items(items)
    assert index.available is True
    assert index.size == 2
    assert index.catalog_path is None
    assert index.get("1")["title"] == "Toy Story"
    assert [it["item_id"] for it in index.search("toy")] == ["1"]
    assert {it["item_id"] for it in index.search("", genre="adventure")} == {"2"}
    # Rows missing an id are skipped (mirrors the file loader's tolerance).
    assert CatalogIndex.from_items([{"title": "no id"}]).size == 0
