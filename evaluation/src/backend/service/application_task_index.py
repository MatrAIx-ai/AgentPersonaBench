"""Cached Playground task discovery with optional on-disk manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import List, Optional

from backend.service.application_task_metadata import (
    ApplicationTaskRecord,
    parse_application_task,
    resolve_playground_entry,
)
from backend.service.playground_task_registry import PlaygroundTaskEntry, resolve_task_kind

_REPO_ROOT = Path(__file__).resolve().parents[4]
_TASKS_DIR = _REPO_ROOT / "application" / "tasks"
_MANIFEST_DIR = _REPO_ROOT / "data" / "cache" / "playground"
_MANIFEST_PATH = _MANIFEST_DIR / "task-index.json"

_CACHE_SIGNATURE: str | None = None
_CACHE_RECORDS: List[ApplicationTaskRecord] | None = None


def tasks_dir_signature(tasks_dir: Path) -> str:
    parts: list[str] = []
    if not tasks_dir.is_dir():
        return ""
    for child in sorted(tasks_dir.iterdir()):
        if not child.is_dir():
            continue
        toml_path = child / "task.toml"
        if toml_path.is_file():
            stat = toml_path.stat()
            parts.append("{}:{}:{}".format(child.name, stat.st_mtime_ns, stat.st_size))
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return "{}:{}".format(len(parts), digest)


def _record_to_manifest_row(record: ApplicationTaskRecord) -> dict[str, object]:
    assert record.playground is not None
    return {
        "folder_name": record.folder_name,
        "task_path": record.task_path,
        "task_name": record.task_name,
        "title": record.title,
        "description": record.description,
        "meta_type": record.meta_type,
        "os": record.os,
        "domain": record.domain,
        "difficulty": record.difficulty,
        "tags": list(record.tags),
        "application_type": record.playground.application_type,
        "task_kind": record.task_kind,
    }


def _record_from_manifest_row(row: dict[str, object]) -> ApplicationTaskRecord | None:
    folder_name = str(row.get("folder_name") or "").strip()
    application_type = str(row.get("application_type") or "").strip()
    meta_type = str(row.get("meta_type") or "").strip()
    os = str(row.get("os") or "").strip().lower()
    if not folder_name or not application_type:
        return None
    playground = resolve_playground_entry(folder_name, meta_type=meta_type, os=os)
    if playground is None:
        playground = PlaygroundTaskEntry(application_type=application_type)
    raw_tags = row.get("tags")
    tags = [str(item) for item in raw_tags] if isinstance(raw_tags, list) else []
    return ApplicationTaskRecord(
        folder_name=folder_name,
        task_path=str(row.get("task_path") or "application/tasks/{}".format(folder_name)),
        task_name=str(row.get("task_name") or ""),
        title=str(row.get("title") or folder_name),
        description=str(row.get("description") or ""),
        meta_type=meta_type,
        os=os,
        domain=str(row.get("domain") or ""),
        difficulty=str(row.get("difficulty") or "easy"),
        tags=tags,
        playground=playground,
        task_kind=str(row.get("task_kind") or resolve_task_kind(folder_name, playground)),
    )


def _load_manifest(signature: str) -> List[ApplicationTaskRecord] | None:
    if not _MANIFEST_PATH.is_file():
        return None
    try:
        payload = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if str(payload.get("signature") or "") != signature:
        return None
    rows = payload.get("tasks")
    if not isinstance(rows, list):
        return None
    records: list[ApplicationTaskRecord] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        record = _record_from_manifest_row(row)
        if record is not None:
            records.append(record)
    return records or None


def _write_manifest(signature: str, records: List[ApplicationTaskRecord]) -> None:
    try:
        _MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "signature": signature,
            "tasks": [_record_to_manifest_row(record) for record in records],
        }
        _MANIFEST_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        return


def _scan_tasks_dir(tasks_dir: Path) -> List[ApplicationTaskRecord]:
    if not tasks_dir.is_dir():
        return []
    records: list[ApplicationTaskRecord] = []
    for child in sorted(tasks_dir.iterdir()):
        if not child.is_dir():
            continue
        record = parse_application_task(child)
        if record is None or record.playground is None:
            continue
        records.append(record)
    return records


def discover_application_task_records(
    *,
    application_type: Optional[str] = None,
    tasks_dir: Path | None = None,
) -> List[ApplicationTaskRecord]:
    """Return Playground-indexed tasks, using memory + on-disk manifest caches."""
    global _CACHE_SIGNATURE, _CACHE_RECORDS

    root = tasks_dir or _TASKS_DIR
    signature = tasks_dir_signature(root)
    if _CACHE_RECORDS is not None and _CACHE_SIGNATURE == signature:
        records = _CACHE_RECORDS
    else:
        records = _load_manifest(signature)
        if records is None:
            records = _scan_tasks_dir(root)
            _write_manifest(signature, records)
        _CACHE_SIGNATURE = signature
        _CACHE_RECORDS = records

    if application_type is None:
        return list(records)
    return [
        record
        for record in records
        if record.playground is not None and record.playground.application_type == application_type
    ]


def clear_application_task_index_cache() -> None:
    """Test helper: drop in-memory discovery cache."""
    global _CACHE_SIGNATURE, _CACHE_RECORDS
    _CACHE_SIGNATURE = None
    _CACHE_RECORDS = None
