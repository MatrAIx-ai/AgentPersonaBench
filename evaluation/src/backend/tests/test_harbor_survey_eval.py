import json

import pytest

from backend.service.survey_types import (
    SurveyEvalConfig,
    SurveyInstrument,
    SurveyQuestion,
    build_survey_eval_result_from_artifacts,
)
from playground.types import Persona


def _instrument() -> SurveyInstrument:
    return SurveyInstrument(
        id="product_attitudes_v1",
        title="Product Attitudes",
        description="A short product concept survey.",
        questions=[
            SurveyQuestion(
                id="concept_fit",
                prompt="This product would fit my needs.",
                type="likert",
                min_value=1,
                max_value=5,
                construct="product_need_fit",
            ),
            SurveyQuestion(
                id="adoption_barrier",
                prompt="What would be your biggest barrier?",
                type="single_choice",
                options=["price", "privacy", "complexity"],
                construct="adoption_barrier",
            ),
        ],
    )


def _survey_payload() -> dict:
    return {
        "instrument": {
            "id": "product_attitudes_v1",
            "title": "Product Attitudes",
        },
        "answers": [
            {
                "questionId": "concept_fit",
                "value": 4,
                "rationale": "The persona is pragmatic but sees a clear use case.",
                "confidence": 0.8,
            },
            {
                "questionId": "adoption_barrier",
                "value": "privacy",
                "rationale": "The persona tends to be cautious about data sharing.",
                "confidence": 0.7,
            },
        ],
        "trajectory": [
            {
                "timestamp": "2026-06-24T00:00:00Z",
                "actor": "system",
                "action": "survey_started",
                "context": {
                    "personaId": "p1",
                    "instrumentId": "product_attitudes_v1",
                },
                "outcome": {},
            },
            {
                "timestamp": "2026-06-24T00:00:01Z",
                "actor": "assistant",
                "action": "ask_question",
                "context": {
                    "questionId": "concept_fit",
                    "construct": "product_need_fit",
                },
                "outcome": {},
            },
            {
                "timestamp": "2026-06-24T00:00:02Z",
                "actor": "user",
                "action": "answer_question",
                "context": {
                    "questionId": "concept_fit",
                    "construct": "product_need_fit",
                },
                "outcome": {
                    "questionId": "concept_fit",
                    "value": 4,
                    "rationale": "The persona is pragmatic but sees a clear use case.",
                    "confidence": 0.8,
                },
            },
            {
                "timestamp": "2026-06-24T00:00:03Z",
                "actor": "assistant",
                "action": "ask_question",
                "context": {
                    "questionId": "adoption_barrier",
                    "construct": "adoption_barrier",
                },
                "outcome": {},
            },
            {
                "timestamp": "2026-06-24T00:00:04Z",
                "actor": "user",
                "action": "answer_question",
                "context": {
                    "questionId": "adoption_barrier",
                    "construct": "adoption_barrier",
                },
                "outcome": {
                    "questionId": "adoption_barrier",
                    "value": "privacy",
                    "rationale": "The persona tends to be cautious about data sharing.",
                    "confidence": 0.7,
                },
            },
            {
                "timestamp": "2026-06-24T00:00:05Z",
                "actor": "system",
                "action": "survey_completed",
                "context": {
                    "personaId": "p1",
                    "instrumentId": "product_attitudes_v1",
                },
                "outcome": {"numAnswered": 2},
            },
        ],
    }


def test_build_survey_eval_result_from_artifacts_maps_answers_trajectory_and_metrics(
    tmp_path,
):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "survey_result.json").write_text(
        json.dumps(_survey_payload()),
        encoding="utf-8",
    )

    result = build_survey_eval_result_from_artifacts(
        output_dir=output_dir,
        config=SurveyEvalConfig(
            persona_model="anthropic/claude-sonnet-4-6",
            mode="harbor_persona_survey",
        ),
        persona=Persona(id="p1", name="Persona One", context="Careful respondent."),
        instrument=_instrument(),
        created_at="2026-06-24T00:00:00Z",
        prompts={
            "harborPrompt": "Careful respondent.",
            "taskPrompt": "Survey task prompt.",
        },
    )

    payload = result.to_dict()
    assert payload["config"]["personaModel"] == "anthropic/claude-sonnet-4-6"
    assert payload["config"]["mode"] == "harbor_persona_survey"
    assert payload["instrument"]["id"] == "product_attitudes_v1"
    assert payload["answers"][0]["value"] == 4
    assert payload["answers"][1]["value"] == "privacy"
    assert payload["metrics"] == {
        "numQuestions": 2,
        "numAnswered": 2,
        "meanLikert": 4.0,
    }
    assert payload["prompts"] == {
        "harborPrompt": "Careful respondent.",
        "taskPrompt": "Survey task prompt.",
    }


def test_build_survey_eval_result_from_artifacts_rejects_bad_trajectory(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    payload = _survey_payload()
    payload["trajectory"][0].pop("outcome")
    (output_dir / "survey_result.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="trajectory event missing"):
        build_survey_eval_result_from_artifacts(
            output_dir=output_dir,
            config=SurveyEvalConfig(mode="harbor_persona_survey"),
            persona=Persona(id="p1", name="Persona One"),
            instrument=_instrument(),
            created_at="2026-06-24T00:00:00Z",
        )
