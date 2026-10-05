"""Tests for the real-bundle catalog (:mod:`backend.service.bundle_catalog`).

These exercise an optional external ``INTERECAGENT_ROOT`` resource bundle
(``resources/<domain>/`` feather item tables), so they require pandas and an
installed bundle. Both are skipped gracefully when absent (a fresh clone / CI
without the large resources) so the core suite still runs everywhere.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("pandas")

from backend.service import bundle_catalog


def _catalog_source_present(domain: str) -> bool:
    """A catalog source exists: the committed parquet (default) or the bundle."""
    parquet = os.path.join(bundle_catalog._catalogs_dir(), "{}.parquet".format(domain))
    bundle = os.path.join(bundle_catalog._resources_root(), domain)
    return os.path.isfile(parquet) or os.path.isdir(bundle)


pytestmark = pytest.mark.skipif(
    not _catalog_source_present("movie"),
    reason="no catalog source (committed parquet or installed bundle) for movie",
)


def test_loads_real_movie_bundle():
    """The movie catalog is the real ~9.9k-item corpus, not the 10-item stub."""
    cat = bundle_catalog.get_bundle_catalog("movie")
    assert cat.available is True
    assert cat.size > 1000
    # A canonical title is findable by case-insensitive substring search.
    hits = cat.search("toy story", limit=5)
    assert any("Toy Story" in (it.get("title") or "") for it in hits)
    # Items carry the normalized shape the wire adapter (catalog_item_view) reads.
    first = hits[0]
    assert isinstance(first.get("item_id"), str) and first["item_id"]
    assert isinstance(first.get("categories"), list)
    assert isinstance(first.get("metadata"), dict)


def test_loads_game_and_beauty_bundles():
    assert bundle_catalog.get_bundle_catalog("game").size > 1000
    assert bundle_catalog.get_bundle_catalog("beauty_product").size > 1000


def test_unknown_domain_is_empty_not_error():
    cat = bundle_catalog.get_bundle_catalog("not-a-domain")
    assert cat.size == 0


def test_caches_per_domain():
    a = bundle_catalog.get_bundle_catalog("movie")
    b = bundle_catalog.get_bundle_catalog("movie")
    assert a is b


def test_build_state_catalog_is_domain_aware(monkeypatch):
    """In production mode (no injected catalog) the app's catalog is the real
    per-domain bundle, and ``catalog_for`` resolves each domain independently."""
    monkeypatch.delenv("INTERECAGENT_CATALOG_PATH", raising=False)
    from backend.api.deps import build_state

    state = build_state(catalog_path=None)
    try:
        assert state.catalog.size > 1000  # default (movie) bundle, not the stub
        assert state.catalog_for("game").size > 1000
        assert state.catalog_for("movie") is not state.catalog_for("game")
    finally:
        state.shutdown()


def test_catalog_endpoint_routes_by_domain(monkeypatch):
    """``GET /api/catalog/search?domain=`` browses that domain's real corpus."""
    monkeypatch.delenv("INTERECAGENT_CATALOG_PATH", raising=False)
    from fastapi.testclient import TestClient

    from backend.api.app import create_app

    app = create_app(catalog_path=None)  # bundle-backed (no injected catalog)
    try:
        with TestClient(app) as client:
            movie = client.get(
                "/api/catalog/search", params={"domain": "movie", "limit": 5}
            ).json()
            game = client.get(
                "/api/catalog/search", params={"domain": "game", "limit": 5}
            ).json()
            assert movie["total"] > 1000 and game["total"] > 1000
            movie_titles = {it["title"] for it in movie["items"]}
            game_titles = {it["title"] for it in game["items"]}
            assert movie_titles and game_titles
            assert movie_titles != game_titles  # distinct per-domain corpora
    finally:
        services = getattr(app.state, "services", None)
        if services is not None:
            services.shutdown()
