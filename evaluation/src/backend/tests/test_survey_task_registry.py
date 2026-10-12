from pathlib import Path

from backend.service.example_task_catalog import repo_root
from backend.service.survey_harbor_tasks import list_survey_harbor_tasks
from backend.service.survey_task_registry import (
    survey_questionnaire_id_for_task_path,
    survey_task_instruction_markdown_for_questionnaire_id,
    survey_task_path_for_questionnaire_id,
)
from playground.survey_task_content import (
    SURVEY_TASK_FOLDER_BY_QUESTIONNAIRE_ID,
    instruction_markdown_for_questionnaire_id,
)


def test_questionnaire_id_for_product_attitudes_task():
    assert (
        survey_questionnaire_id_for_task_path("application/tasks/survey_product-attitudes")
        == "product_attitudes_v1"
    )


def test_questionnaire_id_for_product_feedback_task():
    assert (
        survey_questionnaire_id_for_task_path("application/tasks/example-survey_product-feedback")
        == "product_feedback_v1"
    )


def test_task_path_for_product_attitudes_questionnaire():
    assert (
        survey_task_path_for_questionnaire_id("product_attitudes_v1")
        == "application/tasks/survey_product-attitudes"
    )


def test_task_path_for_product_feedback_questionnaire():
    assert survey_task_path_for_questionnaire_id("product_feedback_v1") == (
        "application/tasks/example-survey_product-feedback"
    )


def test_survey_instruction_markdown_includes_product_concept():
    root = repo_root()
    md = survey_task_instruction_markdown_for_questionnaire_id(
        "product_feedback_v1",
        repo_root=root,
    )
    assert md
    assert "FocusLoop" in md
    assert "q0" in md


def test_harbor_tasks_expose_summary_metadata():
    tasks = list_survey_harbor_tasks()
    assert len(tasks) >= 6
    product = next(
        task for task in tasks if task.task_path.endswith("example-survey_product-feedback")
    )
    assert product.instrument_id == "product_feedback_v1"
    assert product.survey_kind == "example"
    assert product.question_count is not None and product.question_count > 0
    summary = product.to_summary_dict()
    assert summary["instrumentId"] == "product_feedback_v1"
    assert "profileMarkdown" not in summary
    assert "questionnaire" not in summary
    assert not product.profile_markdown
    assert product.questionnaire is None
    contributing = [task for task in tasks if task.survey_kind == "contributing"]
    assert len(contributing) >= 5


def test_harbor_task_detail_includes_full_survey_profile():
    from backend.service.task_detail_service import get_task_detail

    root = repo_root()
    detail = get_task_detail("application/tasks/example-survey_product-feedback", repo_root=root)
    assert "FocusLoop" in detail["profileMarkdown"]
    assert detail["questionnaireMarkdown"].startswith("# Survey Product Feedback")
    assert "Platform-derived answer envelope" in detail["outputSchemaMarkdown"]
    assert detail["questionnaire"] is not None
    assert detail["questionnaire"]["askRationale"] is False
    assert detail["questionnaire"]["askConfidence"] is False
    assert detail["questionnaire"]["questions"][0]["optionDetails"][0]["label"].startswith(
        "Keep using free."
    )


def test_every_questionnaire_id_has_harbor_task_folder():
    root = repo_root()
    for questionnaire_id, folder in SURVEY_TASK_FOLDER_BY_QUESTIONNAIRE_ID.items():
        instruction = root / "application" / "tasks" / folder / "instruction.md"
        assert instruction.is_file(), "missing instruction for {}".format(questionnaire_id)
        assert survey_task_path_for_questionnaire_id(questionnaire_id)


def test_shared_content_module_reads_instruction_md():
    root = repo_root()
    md = instruction_markdown_for_questionnaire_id("product_feedback_v1", repo_root=Path(root))
    assert md
    assert md.startswith("# Survey Product Feedback")
