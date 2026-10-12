"""Tests for :class:`backend.service.session_store.SessionStore`.

Covers save/load round-trip, atomic overwrite, missing-file handling, summary
listing (with the internal ``_mtime`` helper stripped and newest-first order),
export helpers, delete, id validation, and filename sanitization.
"""

from __future__ import annotations

import json
import os

import pytest

from backend.service.session_store import SessionStore


def _session(sid: str, *, title: str = "T", turns=None, messages=None, created="2026-01-01T00:00:00Z"):
    return {
        "id": sid,
        "title": title,
        "config": {"engine": "gpt-4o-mini"},
        "messages": messages if messages is not None else [{"role": "user", "content": "q"}],
        "turns": turns if turns is not None else [{"turnId": "t1"}],
        "createdAt": created,
    }


@pytest.fixture()
def isolated_store(tmp_path):
    return SessionStore(base_dir=os.path.join(str(tmp_path), "store"))


def test_save_then_load_roundtrip(isolated_store):
    data = _session("ses_a")
    path = isolated_store.save(data)
    assert os.path.isfile(path)
    assert isolated_store.load("ses_a") == data


def test_save_creates_directory(tmp_path):
    base = os.path.join(str(tmp_path), "deep", "nested", "store")
    store = SessionStore(base_dir=base)
    assert not os.path.isdir(base)
    store.save(_session("ses_dir"))
    assert os.path.isdir(base)


def test_save_overwrites_atomically(isolated_store):
    isolated_store.save(_session("ses_o", title="first"))
    isolated_store.save(_session("ses_o", title="second"))
    loaded = isolated_store.load("ses_o")
    assert loaded["title"] == "second"
    # No stray temp files left behind.
    files = os.listdir(isolated_store.base_dir)
    assert files == ["ses_o.json"]


def test_load_missing_returns_none(isolated_store):
    assert isolated_store.load("nope") is None


def test_load_corrupt_file_returns_none(isolated_store):
    isolated_store._ensure_dir()
    path = isolated_store.path_for("ses_bad")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("{ this is : not json ]")
    assert isolated_store.load("ses_bad") is None


def test_save_requires_string_id(isolated_store):
    with pytest.raises(ValueError):
        isolated_store.save({"title": "no id"})
    with pytest.raises(ValueError):
        isolated_store.save({"id": ""})


def test_list_empty_when_no_dir(tmp_path):
    store = SessionStore(base_dir=os.path.join(str(tmp_path), "absent"))
    assert store.list() == []


def test_list_summaries_strip_internal_mtime(isolated_store):
    isolated_store.save(_session("ses_1"))
    summaries = isolated_store.list()
    assert len(summaries) == 1
    s = summaries[0]
    assert s["id"] == "ses_1"
    assert s["turnCount"] == 1
    assert s["messageCount"] == 1
    assert "_mtime" not in s


def test_list_orders_newest_first(isolated_store):
    isolated_store.save(_session("ses_old", created="2020-01-01T00:00:00Z"))
    isolated_store.save(_session("ses_new", created="2030-01-01T00:00:00Z"))
    ids = [s["id"] for s in isolated_store.list()]
    assert ids.index("ses_new") < ids.index("ses_old")


def test_list_skips_hidden_and_non_json(isolated_store):
    isolated_store.save(_session("ses_real"))
    # Drop a hidden temp-looking file and a non-json file.
    with open(os.path.join(isolated_store.base_dir, ".hidden.json"), "w") as fh:
        fh.write("{}")
    with open(os.path.join(isolated_store.base_dir, "notes.txt"), "w") as fh:
        fh.write("ignore me")
    ids = [s["id"] for s in isolated_store.list()]
    assert ids == ["ses_real"]


def test_export_returns_json_string(isolated_store):
    isolated_store.save(_session("ses_exp", title="Exportable"))
    exported = isolated_store.export("ses_exp")
    assert exported is not None
    parsed = json.loads(exported)
    assert parsed["id"] == "ses_exp"
    assert parsed["title"] == "Exportable"


def test_export_missing_returns_none(isolated_store):
    assert isolated_store.export("nope") is None


def test_export_dict_static(isolated_store):
    payload = isolated_store.export_dict({"id": "x", "title": "y"})
    assert json.loads(payload) == {"id": "x", "title": "y"}


def test_export_filename(isolated_store):
    assert isolated_store.export_filename("ses_xyz") == "ses_xyz.json"


def test_delete_returns_true_then_false(isolated_store):
    isolated_store.save(_session("ses_del"))
    assert isolated_store.delete("ses_del") is True
    assert isolated_store.delete("ses_del") is False
    assert isolated_store.load("ses_del") is None


def test_path_for_sanitizes_traversal(isolated_store):
    path = isolated_store.path_for("../../etc/passwd")
    # The id is sanitized so the file stays inside base_dir.
    assert os.path.dirname(path) == isolated_store.base_dir
    assert ".." not in os.path.basename(path)
    assert os.path.sep not in os.path.basename(path).replace(".json", "")
