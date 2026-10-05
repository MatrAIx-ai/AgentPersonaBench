"""Registry of Harbor OS app (computer-use) tasks for Playground."""

from __future__ import annotations

from typing import Dict, List

from backend.service.example_task_catalog import discover_application_tasks, task_id_from_folder
from backend.service.os_app_types import OsAppEvalTask
from backend.service.playground_task_registry import (
    default_os_app_backend,
    default_os_app_platform,
    default_environment_label,
)
from backend.service.playground_task_registry_cache import get_cached_registry


def _build_registry() -> Dict[str, OsAppEvalTask]:
    tasks: Dict[str, OsAppEvalTask] = {}
    for record in discover_application_tasks(application_type="os-app"):
        assert record.playground is not None
        pe = record.playground
        os_app_backend = default_os_app_backend(record.meta_type, pe, record.os)
        os_app_platform = (
            pe.os_app_platform or record.os or default_os_app_platform(record.meta_type, os_app_backend, record.os)
        )
        environment_label = pe.environment_label or default_environment_label(os_app_platform)
        task_id = task_id_from_folder(record.folder_name)
        tasks[task_id] = OsAppEvalTask(
            id=task_id,
            title=record.title,
            platform=os_app_platform,
            description=record.description,
            task_path=record.task_path,
            meta_type=record.meta_type,
            os=record.os or os_app_platform,
            domain=record.domain,
            difficulty=record.difficulty,
            task_kind=record.task_kind,
            tags=tuple(record.tags),
            output_artifact=pe.output_artifact or "decision.json",
            os_app_submission_profile=pe.os_app_submission_profile,
            environment_label=environment_label,
            os_app_backend=os_app_backend,
        )
    return tasks


def _registry() -> Dict[str, OsAppEvalTask]:
    return get_cached_registry("os-app", _build_registry)


def list_os_app_eval_tasks() -> List[OsAppEvalTask]:
    return list(_registry().values())


def get_os_app_eval_task(task_id: str) -> OsAppEvalTask:
    try:
        return _registry()[task_id]
    except KeyError as exc:
        raise KeyError("unknown OS app eval task: {}".format(task_id)) from exc
