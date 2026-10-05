"""Task-backed survey questionnaire catalog for Playground survey tasks."""

from __future__ import annotations

from pathlib import Path

from backend.service.example_task_catalog import discover_survey_application_tasks, repo_root
from backend.service.survey_task_registry import survey_questionnaire_id_for_task_path
from playground.survey_task_content import (
    SURVEY_TASK_FOLDER_BY_QUESTIONNAIRE_ID,
    load_survey_task_content_for_questionnaire_id,
)

from .survey_types import SurveyInstrument

__all__ = [
    "DEFAULT_SURVEY_QUESTIONNAIRE_ID",
    "get_survey_questionnaire",
    "list_survey_questionnaires",
]

DEFAULT_SURVEY_QUESTIONNAIRE_ID = "product_attitudes_v1"


def _default_repo_root() -> Path:
    return repo_root()


def _discovered_questionnaire_ids(*, root: Path) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for questionnaire_id in SURVEY_TASK_FOLDER_BY_QUESTIONNAIRE_ID:
        if questionnaire_id not in seen:
            seen.add(questionnaire_id)
            ordered.append(questionnaire_id)
    for record in discover_survey_application_tasks():
        questionnaire_id = survey_questionnaire_id_for_task_path(record.task_path, repo_root=root)
        if not questionnaire_id or questionnaire_id in seen:
            continue
        seen.add(questionnaire_id)
        ordered.append(questionnaire_id)
    return ordered


def list_survey_questionnaires(*, repo_root: Path | None = None) -> list[SurveyInstrument]:
    """Return all task-backed survey questionnaires in stable display order."""
    root = Path(repo_root) if repo_root is not None else _default_repo_root()
    questionnaires: list[SurveyInstrument] = []
    for questionnaire_id in _discovered_questionnaire_ids(root=root):
        try:
            questionnaires.append(get_survey_questionnaire(questionnaire_id, repo_root=root))
        except (FileNotFoundError, KeyError):
            continue
    return questionnaires


def get_survey_questionnaire(
    questionnaire_id: str,
    *,
    repo_root: Path | None = None,
) -> SurveyInstrument:
    """Return one task-backed survey questionnaire loaded from task-local docs."""
    root = Path(repo_root) if repo_root is not None else _default_repo_root()
    from backend.service.survey_task_registry import survey_task_path_for_questionnaire_id

    if survey_task_path_for_questionnaire_id(questionnaire_id, repo_root=root) is None:
        raise KeyError("unknown survey questionnaire: {}".format(questionnaire_id))
    try:
        content = load_survey_task_content_for_questionnaire_id(
            questionnaire_id,
            repo_root=root,
        )
    except Exception as exc:  # noqa: BLE001
        raise FileNotFoundError(
            "failed to load survey questionnaire {} from task input/questionnaire.yaml".format(
                questionnaire_id,
            )
        ) from exc
    if content is None or content.instrument is None:
        raise FileNotFoundError(
            "missing survey questionnaire {} under application/tasks/*/input/questionnaire.yaml".format(
                questionnaire_id,
            )
        )
    return content.instrument
