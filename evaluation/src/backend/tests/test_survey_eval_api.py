"""API contract tests for Playground survey runs.

Survey runs are themselves the evaluation artifact: the persona agent completes
the survey instrument and writes ``survey_result.json``. The API therefore
exposes survey instruments, async run status, and the normalized survey result,
without adding a separate scorecard layer.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("pydantic")


class _FakeSurveyEvalService:
    def __init__(self) -> None:
        self.started: list = []
        self._view: Dict[str, Any] = {
            "jobId": "survey_fake123",
            "applicationType": "survey",
            "taskId": "survey_form",
            "instrumentId": "product_attitudes_v1",
            "instrumentTitle": "Product Attitudes",
            "personaId": "Nemotron_01B0D4D4",
            "personaName": "Persona One",
            "status": "done",
            "phase": None,
            "surveyResult": {
                "instrument": {
                    "id": "product_attitudes_v1",
                    "title": "Product Attitudes",
                    "description": "A short product concept survey.",
                    "questions": [
                        {
                            "id": "concept_fit",
                            "prompt": "This product would fit my needs.",
                            "type": "likert",
                            "minValue": 1,
                            "maxValue": 5,
                            "construct": "product_need_fit",
                            "required": True,
                        }
                    ],
                },
                "answers": [
                    {
                        "questionId": "concept_fit",
                        "value": 4,
                        "rationale": "The persona sees a practical use case.",
                        "confidence": 0.8,
                    }
                ],
                "trajectory": [
                    {
                        "timestamp": "2026-06-24T00:00:00Z",
                        "actor": "system",
                        "action": "survey_started",
                        "context": {"instrumentId": "product_attitudes_v1"},
                        "outcome": {},
                    }
                ],
                "completion": {
                    "numQuestions": 1,
                    "numAnswered": 1,
                    "missingQuestionIds": [],
                    "valid": True,
                },
                "createdAt": "2026-06-24T00:00:00Z",
                "prompts": {
                    "harborPrompt": "Persona prompt",
                    "taskPrompt": "Survey task prompt",
                },
            },
            "prompts": {
                "harborPrompt": "Persona prompt",
                "taskPrompt": "Survey task prompt",
            },
            "error": None,
        }

    def list_instruments(self) -> list:
        return [
            {
                "id": "product_attitudes_v1",
                "title": "Product Attitudes",
                "description": "A short product concept survey.",
                "questions": [
                    {
                        "id": "concept_fit",
                        "prompt": "This product would fit my needs.",
                        "type": "likert",
                        "minValue": 1,
                        "maxValue": 5,
                        "construct": "product_need_fit",
                        "required": True,
                    }
                ],
            }
        ]

    def start(
        self,
        *,
        persona_id: str,
        instrument_id: str,
        persona_model: Optional[str],
        now,
    ) -> str:
        self.started.append(
            {
                "personaId": persona_id,
                "instrumentId": instrument_id,
                "personaModel": persona_model,
                "createdAt": now(),
            }
        )
        return "survey_fake123"

    def view(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._view if job_id == "survey_fake123" else None


@pytest.fixture()
def fake_survey_eval(app):
    fake = _FakeSurveyEvalService()
    app.state.services.survey_eval = fake
    return fake


def test_list_survey_instruments(client, fake_survey_eval):
    resp = client.get("/api/survey-eval/instruments")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["instruments"][0]["id"] == "product_attitudes_v1"
    assert body["instruments"][0]["questions"][0]["id"] == "concept_fit"


def test_start_survey_eval_returns_job_id(client, fake_survey_eval):
    resp = client.post(
        "/api/survey-eval",
        json={
            "personaId": "Nemotron_01B0D4D4",
            "instrumentId": "product_attitudes_v1",
            "personaModel": "anthropic/claude-haiku-4-5",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"jobId": "survey_fake123"}
    assert len(fake_survey_eval.started) == 1
    started = fake_survey_eval.started[0]
    assert started["personaId"] == "Nemotron_01B0D4D4"
    assert started["instrumentId"] == "product_attitudes_v1"
    assert started["personaModel"] == "anthropic/claude-haiku-4-5"
    assert started["createdAt"].endswith("Z")


def test_get_survey_eval_job_returns_survey_result_without_scorecard(
    client, fake_survey_eval
):
    resp = client.get("/api/survey-eval/jobs/survey_fake123")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["applicationType"] == "survey"
    assert body["taskId"] == "survey_form"
    assert body["status"] == "done"
    assert body["surveyResult"]["answers"][0]["questionId"] == "concept_fit"
    assert body["surveyResult"]["completion"]["valid"] is True
    assert "questionnaire" not in body
    assert "metricScores" not in body


def test_get_survey_eval_job_unknown_404(client, fake_survey_eval):
    resp = client.get("/api/survey-eval/jobs/survey_missing")
    assert resp.status_code == 404
