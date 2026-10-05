"""Registry of Playground web application tasks."""

from __future__ import annotations

from typing import Dict, List

from backend.service.example_task_catalog import discover_application_tasks, task_id_from_folder
from backend.service.playground_task_registry_cache import get_cached_registry
from backend.service.web_types import WebEvalTask


def _build_registry() -> Dict[str, WebEvalTask]:
    tasks: Dict[str, WebEvalTask] = {}
    for record in discover_application_tasks(application_type="web"):
        assert record.playground is not None
        pe = record.playground
        task_id = task_id_from_folder(record.folder_name)
        tasks[task_id] = WebEvalTask(
            id=task_id,
            title=record.title,
            site_name=pe.site_name or "Website",
            site_url=pe.site_url or "https://example.com/",
            task_path=record.task_path,
            description=record.description,
            meta_type=record.meta_type,
            domain=record.domain,
            difficulty=record.difficulty,
            task_kind=record.task_kind,
            tags=tuple(record.tags),
            output_artifact=pe.output_artifact or "web_result.json",
            submission_profile=pe.submission_profile or "web_result",
        )
    return tasks


def _registry() -> Dict[str, WebEvalTask]:
    return get_cached_registry("web", _build_registry)


def list_web_eval_tasks() -> List[WebEvalTask]:
    return list(_registry().values())


def get_web_eval_task(task_id: str) -> WebEvalTask:
    try:
        return _registry()[task_id]
    except KeyError as exc:
        raise KeyError("unknown web eval task: {}".format(task_id)) from exc
