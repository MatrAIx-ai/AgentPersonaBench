"""Optional bundle catalog: the searchable item table behind each domain.

When ``INTERECAGENT_ROOT`` points at an external resource checkout, this module
can still load ``resources/<domain>/`` feather tables. Without that optional
checkout, callers get an empty catalog rather than a missing-sidecar error.

This module loads that table (lazily, with pandas) and adapts each row into the
normalized item dict the Studio's :class:`~backend.service.catalog_index.CatalogIndex`
already understands, so the catalog search browses the **real** recommendable
corpus (~9–12k items per domain) instead of a hand-picked stub. Loads are cached
per domain (one process serves a fixed bundle). A missing bundle, missing pandas,
or an unreadable table degrades to an empty index rather than raising — callers
get a valid, empty, searchable catalog.

Importing this module is cheap: pandas is imported lazily inside
:func:`load_bundle_catalog`, only when a domain is first loaded.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from backend.service.catalog_index import CatalogIndex

__all__ = ["get_bundle_catalog", "load_bundle_catalog"]

#: Per-domain cache of loaded indices (process-global; the bundle is immutable).
_cache: Dict[str, CatalogIndex] = {}


def _resources_root() -> str:
    """Absolute path to ``<root>/resources`` (the parent of the domain dirs).

    Honors ``INTERECAGENT_ROOT``. The deleted RecAI sidecar is intentionally not
    a fallback source.
    """
    override = os.environ.get("INTERECAGENT_ROOT")
    if override:
        root = os.path.abspath(override)
    else:
        root = os.path.join(_repo_root(), ".missing-interecagent")
    return os.path.join(root, "resources")


def _repo_root() -> str:
    """Absolute path to the repo root."""
    return str(Path(__file__).resolve().parents[4])


def _chatbot_api_root() -> str:
    """Return the optional external catalog root, if configured."""
    override = os.environ.get("INTERECAGENT_ROOT")
    return os.path.abspath(override) if override else str(Path(_repo_root()) / ".missing-interecagent")


def _catalogs_dir() -> str:
    """Absolute path to the task-owned committed parquet catalogs."""
    return os.path.join(_chatbot_api_root(), "data", "catalogs")


def get_bundle_catalog(domain: str) -> CatalogIndex:
    """Return the (cached) real-bundle catalog for ``domain``.

    Builds it on first request via :func:`load_bundle_catalog` and caches the
    result; later calls return the same index.
    """
    cached = _cache.get(domain)
    if cached is None:
        cached = load_bundle_catalog(domain)
        _cache[domain] = cached
    return cached


def load_bundle_catalog(domain: str) -> CatalogIndex:
    """Load ``domain``'s item table into a fresh :class:`CatalogIndex`.

    Source preference: the committed parquet catalog (``data/catalogs/<domain>.parquet``,
    present on a fresh clone — no big download), else the installed optional bundle's
    feather table (after ``scripts/setup_resources.py``). Any failure (no source,
    no pandas, unreadable) degrades to an empty index.
    """
    frame = _load_domain_frame(domain)
    if frame is None:
        return CatalogIndex.from_items([])
    return CatalogIndex.from_items(_rows_to_items(frame))


def _load_domain_frame(domain: str):
    """Return a domain's item-table DataFrame, or ``None`` if no source loads."""
    try:
        import pandas as pd  # lazy: keeps importing this module cheap
    except Exception:
        return None

    # 1) Committed parquet catalog — works on a fresh clone with no download.
    parquet = os.path.join(_catalogs_dir(), "{}.parquet".format(domain))
    if os.path.isfile(parquet):
        try:
            return pd.read_parquet(parquet)
        except Exception:
            pass

    # 2) Installed optional bundle feather table (settings.json names the file).
    domain_dir = os.path.join(_resources_root(), domain)
    settings_path = os.path.join(domain_dir, "settings.json")
    if os.path.isfile(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as fh:
                settings = json.load(fh)
            info_file = str(settings.get("GAME_INFO_FILE") or "")
            table_path = os.path.join(domain_dir, info_file)
            if info_file and os.path.isfile(table_path):
                return pd.read_feather(table_path)
        except Exception:
            pass
    return None


# --------------------------------------------------------------------------- #
# Row normalization (feather row -> normalized item dict)
# --------------------------------------------------------------------------- #
#: feather column -> metadata key exposed on the normalized item.
_METADATA_COLS = (
    ("release_date", "releaseDate"),
    ("price", "price"),
    ("brand", "brand"),
    ("visited_num", "popularity"),
)


def _rows_to_items(frame: Any) -> List[Dict[str, Any]]:
    """Normalize a domain item table into ``CatalogIndex`` item dicts.

    Maps the bundle's columns onto the canonical shape (``item_id`` / ``title``
    / ``description`` / ``categories`` / ``metadata``). Categories come from the
    domain's list column (``tags`` for movie/game, ``category`` for beauty).
    Rows are ordered most-popular-first so empty-query "browse" surfaces
    recognizable items.
    """
    columns = set(getattr(frame, "columns", []))
    if "visited_num" in columns:
        frame = frame.sort_values("visited_num", ascending=False)
    category_col = "tags" if "tags" in columns else ("category" if "category" in columns else None)

    items: List[Dict[str, Any]] = []
    for row in frame.to_dict("records"):
        item_id = row.get("id")
        title = row.get("title")
        if item_id is None or title is None:
            continue
        item: Dict[str, Any] = {
            "item_id": str(item_id),
            "title": str(title),
            "categories": _as_str_list(row.get(category_col)) if category_col else [],
            "metadata": {
                meta_key: _scalar(row[col])
                for col, meta_key in _METADATA_COLS
                if col in columns and row.get(col) is not None
            },
        }
        description = row.get("description")
        if isinstance(description, str) and description.strip():
            item["description"] = description
        items.append(item)
    return items


def _as_str_list(value: Any) -> List[str]:
    """Coerce a categorical cell (list / numpy array / None) to a list of str."""
    if value is None:
        return []
    try:
        sequence = list(value)
    except TypeError:
        return []
    out: List[str] = []
    for entry in sequence:
        if entry is None:
            continue
        text = str(entry).strip()
        if text:
            out.append(text)
    return out


def _scalar(value: Any) -> Any:
    """Normalize a numpy/pandas scalar to a JSON-friendly Python value."""
    if hasattr(value, "item"):  # numpy scalar (np.int64, np.float64, ...)
        try:
            value = value.item()
        except Exception:  # pragma: no cover - defensive
            pass
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
