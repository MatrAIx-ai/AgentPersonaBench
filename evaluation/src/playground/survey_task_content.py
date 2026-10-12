"""Load task-backed survey content and questionnaires."""

from __future__ import annotations

from pathlib import Path

import yaml

from backend.service.survey_instruction_builder import (
    render_survey_context_markdown,
    render_survey_output_schema_markdown,
    render_survey_questionnaire_markdown,
    render_survey_task_instruction_markdown,
)
from backend.service.survey_types import SurveyInstrument, SurveyTaskContent
from playground.survey_list_meta import read_survey_questionnaire_list_meta
from playground.task_content_bundle import (
    content_dir_for_task_path,
    input_dir_for_task_path,
    load_task_content_bundle_for_task_path,
    task_dir_from_path,
)

# questionnaire id → ``application/tasks/`` folder name.
# Only ``example-survey_product-feedback`` is a contributor reference example;
# the other folders are real application survey tasks (``survey_*``).
SURVEY_TASK_FOLDER_BY_QUESTIONNAIRE_ID: dict[str, str] = {
    "product_attitudes_v1": "survey_product-attitudes",
    "product_feedback_v1": "example-survey_product-feedback",
    "software_claude_code_vscode_checkpoints_v1": "survey_claude-code-vscode-checkpoints",
    "finance_robinhood_cortex_digests_v1": "survey_robinhood-cortex-digests",
    "healthcare_cvs_app_prescription_ai_v1": "survey_cvs-prescription-ai",
    "commerce_nike_air_max_dn_dynamic_air_v1": "survey_nike-air-max-dn",
}

_TASK_FOLDER_BY_QUESTIONNAIRE_ID = SURVEY_TASK_FOLDER_BY_QUESTIONNAIRE_ID


def is_example_survey_task_folder(folder: str) -> bool:
    return folder.startswith("example-survey_")


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def survey_questionnaire_id_for_task_folder(folder: str, *, repo_root: Path | None = None) -> str | None:
    for questionnaire_id, mapped_folder in _TASK_FOLDER_BY_QUESTIONNAIRE_ID.items():
        if mapped_folder == folder:
            return questionnaire_id
    root = repo_root or _default_repo_root()
    questionnaire_id, _ = read_survey_questionnaire_list_meta(root / "application" / "tasks" / folder)
    return questionnaire_id


def survey_task_folder_for_questionnaire_id(
    questionnaire_id: str,
    *,
    repo_root: Path | None = None,
) -> str | None:
    mapped = _TASK_FOLDER_BY_QUESTIONNAIRE_ID.get(questionnaire_id)
    if mapped:
        return mapped
    root = repo_root or _default_repo_root()
    tasks_dir = root / "application" / "tasks"
    if not tasks_dir.is_dir():
        return None
    for child in sorted(tasks_dir.iterdir()):
        if not child.is_dir():
            continue
        if not (child.name.startswith("survey_") or child.name.startswith("example-survey_")):
            continue
        qid, _ = read_survey_questionnaire_list_meta(child)
        if qid == questionnaire_id:
            return child.name
    return None


def survey_task_path_for_questionnaire_id(
    questionnaire_id: str,
    *,
    repo_root: Path | None = None,
) -> str | None:
    folder = survey_task_folder_for_questionnaire_id(questionnaire_id, repo_root=repo_root)
    if not folder:
        return None
    return "application/tasks/{}".format(folder)


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _read_yaml(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    return payload if isinstance(payload, dict) else None


def _questionnaire_from_questionnaire_yaml(
    payload: dict | None,
    *,
    questionnaire_id: str,
    default_title: str,
    default_description: str = "",
) -> SurveyInstrument | None:
    if not isinstance(payload, dict):
        return None
    normalized = dict(payload)
    normalized.setdefault("id", questionnaire_id)
    normalized.setdefault("title", default_title)
    normalized.setdefault("description", default_description)
    try:
        return SurveyInstrument.from_dict(normalized)
    except Exception:  # noqa: BLE001
        return None


def load_survey_task_content_for_task_path(
    task_path: str,
    *,
    repo_root: Path,
    questionnaire_id: str | None = None,
    fallback_questionnaire: SurveyInstrument | None = None,
) -> SurveyTaskContent:
    input_dir = input_dir_for_task_path(task_path, repo_root=repo_root)
    content_dir = content_dir_for_task_path(task_path, repo_root=repo_root)
    bundle = load_task_content_bundle_for_task_path(task_path, repo_root=repo_root)
    instruction_markdown = bundle.instruction_markdown
    context_markdown = bundle.context_markdown
    questionnaire_markdown = ""
    output_schema_markdown = bundle.output_schema_markdown
    questionnaire_yaml = None
    if input_dir is not None:
        questionnaire_yaml = _read_yaml(input_dir / "questionnaire.yaml")
    if content_dir is not None:
        questionnaire_yaml = questionnaire_yaml or _read_yaml(content_dir / "questionnaire.yaml")
    task_dir = task_dir_from_path(task_path, repo_root=repo_root)
    title = (
        fallback_questionnaire.title if fallback_questionnaire else task_dir.name.replace("-", " ")
    )
    if not instruction_markdown and fallback_questionnaire is not None:
        instruction_markdown = render_survey_task_instruction_markdown(fallback_questionnaire).strip()
    if not context_markdown and fallback_questionnaire is not None:
        context_markdown = render_survey_context_markdown(fallback_questionnaire).strip()
    parsed_questionnaire = (
        _questionnaire_from_questionnaire_yaml(
            questionnaire_yaml,
            questionnaire_id=questionnaire_id
            or (fallback_questionnaire.id if fallback_questionnaire else task_dir.name),
            default_title=title,
            default_description=context_markdown,
        )
        if questionnaire_yaml is not None
        else None
    )
    effective_questionnaire = parsed_questionnaire or fallback_questionnaire
    if not questionnaire_markdown and effective_questionnaire is not None:
        questionnaire_markdown = render_survey_questionnaire_markdown(effective_questionnaire).strip()
    if not output_schema_markdown and effective_questionnaire is not None:
        output_schema_markdown = render_survey_output_schema_markdown(effective_questionnaire).strip()
    return SurveyTaskContent(
        title=effective_questionnaire.title if effective_questionnaire else title,
        task_path=task_path,
        instruction_markdown=instruction_markdown,
        context_markdown=context_markdown,
        questionnaire_markdown=questionnaire_markdown,
        output_schema_markdown=output_schema_markdown,
        instrument=effective_questionnaire,
    )


def load_survey_task_content_for_questionnaire_id(
    questionnaire_id: str,
    *,
    repo_root: Path,
    fallback_questionnaire: SurveyInstrument | None = None,
) -> SurveyTaskContent | None:
    task_path = survey_task_path_for_questionnaire_id(questionnaire_id, repo_root=repo_root)
    if not task_path:
        return None
    return load_survey_task_content_for_task_path(
        task_path,
        repo_root=repo_root,
        questionnaire_id=questionnaire_id,
        fallback_questionnaire=fallback_questionnaire,
    )


def instruction_markdown_for_questionnaire_id(
    questionnaire_id: str,
    *,
    repo_root: Path,
) -> str | None:
    """Return combined markdown when this questionnaire id maps to survey task content."""
    content = load_survey_task_content_for_questionnaire_id(
        questionnaire_id,
        repo_root=repo_root,
    )
    if content is None:
        return None
    text = content.combined_markdown().strip()
    return text or None


# Compatibility aliases for older instrument-centric imports.
SURVEY_INSTRUMENT_TASK_FOLDERS = SURVEY_TASK_FOLDER_BY_QUESTIONNAIRE_ID
instrument_id_for_task_folder = survey_questionnaire_id_for_task_folder
task_folder_for_instrument = survey_task_folder_for_questionnaire_id
task_path_for_instrument = survey_task_path_for_questionnaire_id
load_survey_task_content_for_instrument = load_survey_task_content_for_questionnaire_id
instruction_markdown_for_instrument = instruction_markdown_for_questionnaire_id
