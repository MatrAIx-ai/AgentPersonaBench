"""In-memory index over the normalized recommendation catalog.

The catalog is a JSONL file (one item per line) produced by the MatrAIx
normalization pipeline. Each line looks like::

    {
      "item_id": "cmu:54166",
      "domain": "movie",
      "title": "The Maltese Falcon",
      "description": "...",
      "display_text": "...",
      "categories": ["Film-noir", "Mystery", "Detective"],
      "metadata": {"release_year": 1941, ...},
      "signals": {...},
      "source": {...}
    }

:class:`CatalogIndex` loads the whole file **once** with the standard-library
``json`` module (deliberately NO pandas / numpy, per the architecture: the
catalog has ~42k items and must load with stdlib only), then offers:

* :meth:`search` -- case-insensitive substring search over title / description
  / categories, optionally filtered by genre, capped by ``limit``;
* :meth:`get` -- fetch a single item by id;
* :meth:`title_for` -- convenience for resolving an id to its title.

A missing or unreadable catalog file is tolerated: the index is simply empty
and :attr:`available` is ``False`` (the rest of the app degrades gracefully).
"""

from __future__ import annotations

import json
import os
from typing import Dict, Iterable, List, Optional

__all__ = ["CatalogIndex"]


class CatalogIndex:
    """Loads ``items.jsonl`` once and serves cheap search / lookup.

    Parameters
    ----------
    catalog_path:
        Path to the normalized ``items.jsonl``. If ``None``, missing, or
        unreadable, the index loads empty and :attr:`available` is ``False``.
    """

    def __init__(self, catalog_path: Optional[str]):
        self.catalog_path: Optional[str] = catalog_path
        self.available: bool = False
        #: ordered list of raw item dicts as they appear in the file
        self._items: List[Dict[str, object]] = []
        #: item_id -> item dict
        self._by_id: Dict[str, Dict[str, object]] = {}
        #: parallel list of pre-lowercased haystacks for fast substring search
        self._haystacks: List[str] = []
        self._load()

    # ------------------------------------------------------------------ #
    # Construction
    # ------------------------------------------------------------------ #
    @classmethod
    def from_items(cls, items: Iterable[Dict[str, object]]) -> "CatalogIndex":
        """Build an index directly from already-normalized item dicts (no file).

        This is the constructor the real-bundle catalog uses: a domain's items
        are read from its feather table (not a JSONL file) and handed here as
        dicts shaped like normalized items (``item_id`` / ``title`` /
        ``categories`` / ``metadata``). Rows that are not dicts or lack a string
        ``item_id`` are skipped, mirroring the file loader's tolerance. The
        resulting index is :attr:`available` (``catalog_path`` stays ``None``).
        """
        index = cls(None)
        index._ingest(items)
        return index

    # ------------------------------------------------------------------ #
    # Loading
    # ------------------------------------------------------------------ #
    def _load(self) -> None:
        path = self.catalog_path
        if not path or not os.path.isfile(path):
            return
        parsed: List[Dict[str, object]] = []
        try:
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        # Skip malformed lines rather than fail the whole load.
                        continue
                    parsed.append(obj)
        except OSError:
            # File vanished / permission error mid-read: behave as unavailable.
            return
        self._ingest(parsed)

    def _ingest(self, rows: Iterable[Dict[str, object]]) -> None:
        """Index an iterable of raw item dicts, skipping non-dict / no-id rows.

        Shared by the JSONL loader and :meth:`from_items`. Sets the index to
        :attr:`available` even when ``rows`` is empty (the ingest itself
        succeeded; it simply found nothing to index).
        """
        items: List[Dict[str, object]] = []
        by_id: Dict[str, Dict[str, object]] = {}
        haystacks: List[str] = []
        for obj in rows:
            if not isinstance(obj, dict):
                continue
            item_id = obj.get("item_id")
            if not isinstance(item_id, str) or not item_id:
                continue
            items.append(obj)
            by_id[item_id] = obj
            haystacks.append(self._haystack_for(obj))
        self._items = items
        self._by_id = by_id
        self._haystacks = haystacks
        self.available = True

    @staticmethod
    def _haystack_for(item: Dict[str, object]) -> str:
        """Build a single lowercased string to substring-match against."""
        parts: List[str] = []
        title = item.get("title")
        if isinstance(title, str):
            parts.append(title)
        description = item.get("description")
        if isinstance(description, str):
            parts.append(description)
        for cat in CatalogIndex._categories_of(item):
            parts.append(cat)
        return " ".join(parts).lower()

    @staticmethod
    def _categories_of(item: Dict[str, object]) -> List[str]:
        cats = item.get("categories")
        if isinstance(cats, list):
            return [c for c in cats if isinstance(c, str)]
        return []

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def __len__(self) -> int:
        return len(self._items)

    @property
    def size(self) -> int:
        """Number of indexed items."""
        return len(self._items)

    def get(self, item_id: str) -> Optional[Dict[str, object]]:
        """Return the raw item dict for ``item_id``, or ``None`` if unknown."""
        if not item_id:
            return None
        return self._by_id.get(item_id)

    def title_for(self, item_id: str) -> Optional[str]:
        """Return the title for ``item_id``, or ``None`` if unknown/untitled."""
        item = self.get(item_id)
        if item is None:
            return None
        title = item.get("title")
        return title if isinstance(title, str) else None

    def search(
        self,
        q: str = "",
        genre: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, object]]:
        """Case-insensitive search over title / description / categories.

        Parameters
        ----------
        q:
            Substring query. Empty / whitespace matches everything (subject to
            ``genre`` and ``limit``), which is handy for "browse" mode.
        genre:
            If given, only items whose ``categories`` contain a case-insensitive
            match (substring) for this genre are returned.
        limit:
            Maximum number of results. Non-positive disables the cap.

        Returns the matching raw item dicts in catalog order (a stable,
        deterministic order), never more than ``limit`` of them.
        """
        needle = (q or "").strip().lower()
        genre_needle = (genre or "").strip().lower()
        results: List[Dict[str, object]] = []
        for idx, item in enumerate(self._items):
            if needle and needle not in self._haystacks[idx]:
                continue
            if genre_needle and not self._matches_genre(item, genre_needle):
                continue
            results.append(item)
            if limit and limit > 0 and len(results) >= limit:
                break
        return results

    def count(self, q: str = "", genre: Optional[str] = None) -> int:
        """Total number of items matching ``q`` / ``genre`` (ignoring limit)."""
        needle = (q or "").strip().lower()
        genre_needle = (genre or "").strip().lower()
        if not needle and not genre_needle:
            return len(self._items)
        total = 0
        for idx, item in enumerate(self._items):
            if needle and needle not in self._haystacks[idx]:
                continue
            if genre_needle and not self._matches_genre(item, genre_needle):
                continue
            total += 1
        return total

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    @staticmethod
    def _matches_genre(item: Dict[str, object], genre_needle: str) -> bool:
        for cat in CatalogIndex._categories_of(item):
            if genre_needle in cat.lower():
                return True
        return False
