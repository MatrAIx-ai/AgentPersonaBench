"""Map survey task paths to questionnaire metadata ids."""

from __future__ import annotations

from pathlib import Path

from playground.survey_task_content import (
    instruction_markdown_for_questionnaire_id as _instruction_md,
    load_survey_task_content_for_questionnaire_id,
    survey_questionnaire_id_for_task_folder,
    survey_task_folder_for_questionnaire_id,
)


def survey_questionnaire_id_for_task_path(task_path: str, *, repo_root: Path | None = None) -> str | None:
    folder = Path(task_path.strip().replace("\\", "/")).name
    return survey_questionnaire_id_for_task_folder(folder, repo_root=repo_root)


def survey_task_path_for_questionnaire_id(questionnaire_id: str, *, repo_root: Path | None = None) -> str | None:
    folder = survey_task_folder_for_questionnaire_id(questionnaire_id, repo_root=repo_root)
    if not folder:
        return None
    return "application/tasks/{}".format(folder)


def survey_task_instruction_markdown_for_questionnaire_id(
    questionnaire_id: str,
    *,
    repo_root: Path,
) -> str | None:
    """Return combined task markdown for a questionnaire id mapped to a survey task."""
    direct = _instruction_md(questionnaire_id, repo_root=repo_root)
    if direct:
        return direct
    content = load_survey_task_content_for_questionnaire_id(questionnaire_id, repo_root=repo_root)
    if content is not None:
        combined = content.combined_markdown().strip()
        if combined:
            return combined
    task_path = survey_task_path_for_questionnaire_id(questionnaire_id, repo_root=repo_root)
    if not task_path:
        return None
    from backend.service.task_detail_service import get_task_detail

    try:
        detail = get_task_detail(task_path, repo_root=repo_root)
    except (FileNotFoundError, ValueError, OSError):
        return None
    instruction_md = str(detail.get("instructionMarkdown") or "").strip()
    if instruction_md:
        return instruction_md
    profile = str(detail.get("profileMarkdown") or "").strip()
    return profile or None


# Compatibility aliases for older instrument-centric imports.
instrument_id_for_task_path = survey_questionnaire_id_for_task_path
task_path_for_instrument = survey_task_path_for_questionnaire_id
survey_instruction_markdown_for_instrument = survey_task_instruction_markdown_for_questionnaire_id
