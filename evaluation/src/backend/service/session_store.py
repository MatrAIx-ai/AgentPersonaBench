"""On-disk JSON persistence for Studio sessions.

Sessions are stored as individual JSON files under a base directory (default
``data/cache/playground/harness_sessions`` relative to the repo
root). The directory is gitignored and created on demand.

The store is intentionally dumb: it round-trips plain session dicts and offers a
lightweight :meth:`list` of summaries for the session rail. It does no locking
(the single-worker API serializes writes through the session manager) and no
schema validation beyond requiring an ``id``.
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Dict, List, Optional

__all__ = ["SessionStore"]


def _default_base_dir() -> str:
    here = os.path.abspath(__file__)
    # session_store.py -> service -> backend -> playground ->
    # applications -> <repo root>
    repo_root = here
    for _ in range(5):
        repo_root = os.path.dirname(repo_root)
    return os.path.join(
        repo_root,
        "data",
        "cache",
        "playground",
        "harness_sessions",
    )


class SessionStore:
    """Persist and load session dicts as JSON files in ``base_dir``."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir: str = base_dir or _default_base_dir()

    # ------------------------------------------------------------------ #
    # Paths / dir management
    # ------------------------------------------------------------------ #
    def _ensure_dir(self) -> None:
        os.makedirs(self.base_dir, exist_ok=True)

    def path_for(self, session_id: str) -> str:
        """Absolute path to the JSON file backing ``session_id``."""
        return os.path.join(self.base_dir, "{}.json".format(_safe_id(session_id)))

    # ------------------------------------------------------------------ #
    # Read / write
    # ------------------------------------------------------------------ #
    def save(self, session_dict: Dict[str, Any]) -> str:
        """Persist ``session_dict`` (must contain ``id``); return the file path.

        Writes atomically (temp file + ``os.replace``) so a crashed write never
        leaves a half-written session file behind.
        """
        session_id = session_dict.get("id")
        if not isinstance(session_id, str) or not session_id:
            raise ValueError("session_dict must contain a non-empty string 'id'")
        self._ensure_dir()
        path = self.path_for(session_id)
        payload = json.dumps(session_dict, ensure_ascii=False, indent=2)
        fd, tmp_path = tempfile.mkstemp(
            prefix=".{}.".format(_safe_id(session_id)),
            suffix=".tmp",
            dir=self.base_dir,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
            os.replace(tmp_path, path)
        except BaseException:
            # Clean up the temp file on any failure, then re-raise.
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            raise
        return path

    def load(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load and return the session dict for ``session_id`` (or ``None``)."""
        path = self.path_for(session_id)
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as fh:
                obj = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return None
        return obj if isinstance(obj, dict) else None

    def delete(self, session_id: str) -> bool:
        """Remove the session file; return ``True`` if it existed."""
        path = self.path_for(session_id)
        try:
            os.remove(path)
            return True
        except OSError:
            return False

    def export(self, session_id: str) -> Optional[str]:
        """Return the session's JSON as a pretty string for download, or ``None``.

        Used by ``GET /api/sessions/{id}/export``. The API serves this body with
        a ``Content-Disposition: attachment`` header. Returns ``None`` if the
        session is not on disk so the API can answer 404. Prefer
        :meth:`export_dict` when the caller already holds the live session dict.
        """
        data = self.load(session_id)
        if data is None:
            return None
        return self.export_dict(data)

    @staticmethod
    def export_dict(session_dict: Dict[str, Any]) -> str:
        """Serialize an in-memory session dict to the canonical export JSON."""
        return json.dumps(session_dict, ensure_ascii=False, indent=2)

    def export_filename(self, session_id: str) -> str:
        """Suggested download filename for a session export."""
        return "{}.json".format(_safe_id(session_id))

    def list(self) -> List[Dict[str, Any]]:
        """Return summary dicts for every stored session, newest first.

        Each summary is::

            {"id", "title", "config", "turnCount", "messageCount", "createdAt"}

        Sorted by ``createdAt`` descending (falling back to mtime / filename so
        ordering is always deterministic).
        """
        if not os.path.isdir(self.base_dir):
            return []
        summaries: List[Dict[str, Any]] = []
        for name in os.listdir(self.base_dir):
            if not name.endswith(".json") or name.startswith("."):
                continue
            path = os.path.join(self.base_dir, name)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    obj = json.load(fh)
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(obj, dict) or not isinstance(obj.get("id"), str):
                continue
            summaries.append(self._summarize(obj, path))
        summaries.sort(key=_summary_sort_key, reverse=True)
        # Drop the internal sort helper before returning to callers.
        for summary in summaries:
            summary.pop("_mtime", None)
        return summaries

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    @staticmethod
    def _summarize(obj: Dict[str, Any], path: str) -> Dict[str, Any]:
        turns = obj.get("turns")
        messages = obj.get("messages")
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            mtime = 0.0
        return {
            "id": obj.get("id"),
            "title": obj.get("title"),
            "config": obj.get("config"),
            "turnCount": len(turns) if isinstance(turns, list) else 0,
            "messageCount": len(messages) if isinstance(messages, list) else 0,
            "createdAt": obj.get("createdAt"),
            "_mtime": mtime,
        }


def _safe_id(session_id: str) -> str:
    """Sanitize a session id for use as a filename (defense in depth)."""
    return "".join(c if (c.isalnum() or c in "-_") else "_" for c in session_id)


def _summary_sort_key(summary: Dict[str, Any]):
    created = summary.get("createdAt")
    created_key = created if isinstance(created, str) else ""
    mtime = summary.get("_mtime")
    mtime_key = mtime if isinstance(mtime, (int, float)) else 0.0
    sid = summary.get("id")
    id_key = sid if isinstance(sid, str) else ""
    return (created_key, mtime_key, id_key)
