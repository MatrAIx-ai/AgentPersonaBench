"""Discover Harbor application tasks for Playground from ``application/tasks/*/task.toml``."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from backend.service.application_task_index import discover_application_task_records
from backend.service.application_task_metadata import ApplicationTaskRecord
from backend.service.application_types import CANONICAL_APPLICATION_TYPES, normalize_metadata_type
from backend.service.playground_task_registry import get_playground_entry

_REPO_ROOT = Path(__file__).resolve().parents[4]
_TASKS_DIR = _REPO_ROOT / "application" / "tasks"


def repo_root() -> Path:
    return _REPO_ROOT


def task_id_from_folder(folder_name: str) -> str:
    slug = folder_name
    stripped = False
    for prefix in ("example-survey_", "survey_"):
        if slug.startswith(prefix):
            slug = slug[len(prefix) :]
            stripped = True
            break
    if not stripped and slug.startswith("example-"):
        slug = slug[len("example-") :]
    return slug.replace("_", "-")


def survey_task_slug(folder_name: str) -> str:
    """Strip ``example-survey_`` or ``survey_`` prefix from a task folder name."""
    for prefix in ("example-survey_", "survey_"):
        if folder_name.startswith(prefix):
            return folder_name[len(prefix) :]
    return folder_name


def discover_application_tasks(
    *,
    application_type: Optional[str] = None,
) -> List[ApplicationTaskRecord]:
    """Return tasks indexed in Playground with Harbor metadata from task.toml."""
    return discover_application_task_records(application_type=application_type, tasks_dir=_TASKS_DIR)


# Backward-compatible aliases used by existing imports/tests.
ExampleTaskRecord = ApplicationTaskRecord


def categorize_task(folder_name: str, meta_type: str) -> Optional[str]:
    entry = get_playground_entry(folder_name)
    if entry is not None:
        return entry.application_type
    normalized = normalize_metadata_type(meta_type)
    if normalized in CANONICAL_APPLICATION_TYPES:
        return normalized
    return None


def discover_example_tasks(*, category: Optional[str] = None) -> List[ApplicationTaskRecord]:
    return [
        record
        for record in discover_application_tasks(application_type=category)
        if record.folder_name.startswith("example-")
    ]


def discover_survey_application_tasks() -> List[ApplicationTaskRecord]:
    return discover_application_tasks(application_type="survey")
