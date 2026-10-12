"""Tests for task-backed Playground survey questionnaires."""

from __future__ import annotations

import pytest

from backend.service.example_task_catalog import repo_root
from backend.service.survey_questionnaire_catalog import (
    DEFAULT_SURVEY_QUESTIONNAIRE_ID,
    get_survey_questionnaire,
    list_survey_questionnaires,
)
from playground.survey_task_content import (
    load_survey_task_content_for_questionnaire_id,
)


REAL_FEATURE_SURVEY_IDS = [
    "product_feedback_v1",
    "software_claude_code_vscode_checkpoints_v1",
    "finance_robinhood_cortex_digests_v1",
    "healthcare_cvs_app_prescription_ai_v1",
    "commerce_nike_air_max_dn_dynamic_air_v1",
]


def test_list_survey_questionnaires_includes_real_feature_surveys():
    questionnaires = list_survey_questionnaires()
    ids = [questionnaire.id for questionnaire in questionnaires]

    assert len(ids) >= 6
    for feature_id in REAL_FEATURE_SURVEY_IDS:
        assert feature_id in ids
    assert DEFAULT_SURVEY_QUESTIONNAIRE_ID in ids

    for questionnaire in questionnaires:
        assert questionnaire.title
        assert questionnaire.description
        assert len(questionnaire.questions) >= 4
        assert all(question.id for question in questionnaire.questions)
        assert all(question.prompt for question in questionnaire.questions)
        assert all(question.construct for question in questionnaire.questions)


def test_get_survey_questionnaire_returns_real_feature_survey():
    questionnaire = get_survey_questionnaire("commerce_nike_air_max_dn_dynamic_air_v1")

    assert questionnaire.title == "Nike Air Max Dn Dynamic Air Purchase Survey"
    assert [question.id for question in questionnaire.questions] == [
        "dynamic_air_appeal",
        "comfort_price_tolerance",
        "purchase_driver",
        "proof_requirement",
    ]


def test_get_survey_questionnaire_unknown_id_raises_keyerror():
    with pytest.raises(KeyError, match="unknown survey questionnaire"):
        get_survey_questionnaire("missing_survey")


def test_repo_backed_survey_questionnaire_loads_structured_option_labels():
    questionnaire = get_survey_questionnaire("product_feedback_v1", repo_root=repo_root())

    first = questionnaire.questions[0]
    assert first.id == "q0"
    assert first.options[0] == "q0_use_free_wont_pay"
    assert first.option_details
    assert first.option_details[0].label.startswith("Keep using free.")


def test_repo_backed_survey_task_content_uses_task_input_without_infra_copy():
    questionnaire = get_survey_questionnaire("product_attitudes_v1", repo_root=repo_root())
    content = load_survey_task_content_for_questionnaire_id(
        questionnaire.id,
        repo_root=repo_root(),
        fallback_questionnaire=questionnaire,
    )

    assert content is not None
    assert "Product Attitudes" in content.instruction_markdown
    assert "input/output_schema.md" not in content.instruction_markdown
    assert "/app/output/survey_result.json" not in content.instruction_markdown
    assert "backend/runtime" not in content.instruction_markdown
    assert "Platform-derived answer envelope" in content.output_schema_markdown
    assert "backend/runtime" not in content.output_schema_markdown
    assert '"trajectory"' not in content.output_schema_markdown
    assert content.instrument is not None
    assert content.instrument.ask_rationale is False
    assert content.instrument.ask_confidence is False
