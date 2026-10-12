"""Harbor survey tasks for Playground (reference example + contributing tasks)."""

from __future__ import annotations

from typing import Dict, List

from backend.service.example_task_catalog import (
    discover_survey_application_tasks,
    repo_root,
    task_id_from_folder,
)
from backend.service.survey_harbor_types import SurveyHarborTask
from backend.service.survey_task_registry import survey_questionnaire_id_for_task_path
from backend.service.task_list_summary import read_survey_questionnaire_list_meta
from backend.service.playground_task_registry_cache import get_cached_registry


def _build_registry() -> Dict[str, SurveyHarborTask]:
    tasks: Dict[str, SurveyHarborTask] = {}
    root = repo_root()
    for record in discover_survey_application_tasks():
        task_dir = root / record.task_path
        yaml_questionnaire_id, question_count = read_survey_questionnaire_list_meta(task_dir)
        questionnaire_id = survey_questionnaire_id_for_task_path(record.task_path, repo_root=root) or yaml_questionnaire_id or ""
        if not questionnaire_id:
            continue
        task_id = "harbor-{}".format(task_id_from_folder(record.folder_name))
        tasks[task_id] = SurveyHarborTask(
            id=task_id,
            title=record.title,
            description=record.description,
            task_path=record.task_path,
            instrument_id=questionnaire_id,
            question_count=question_count,
            survey_kind="example" if record.task_kind == "example" else "contributing",
            meta_type=record.meta_type,
            domain=record.domain,
            difficulty=record.difficulty,
            task_kind=record.task_kind,
            tags=tuple(record.tags),
        )
    return tasks


def _registry() -> Dict[str, SurveyHarborTask]:
    return get_cached_registry("survey", _build_registry)


def list_survey_harbor_tasks() -> List[SurveyHarborTask]:
    return list(_registry().values())


def get_survey_harbor_task(task_id: str) -> SurveyHarborTask:
    try:
        return _registry()[task_id]
    except KeyError as exc:
        raise KeyError("unknown survey harbor task: {}".format(task_id)) from exc
