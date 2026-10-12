"""API contract tests for Playground AppWorld runs."""

from __future__ import annotations

from typing import Any, Dict, Optional

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("pydantic")


class _FakeAppWorldEvalService:
    def __init__(self) -> None:
        self.started: list[dict[str, Any]] = []
        self._view: Dict[str, Any] = {
            "jobId": "appworld_fake123",
            "applicationType": "appworld",
            "taskId": "appworld-demo-personal-admin",
            "taskTitle": "AppWorld personal admin task",
            "appName": "AppWorld",
            "personaId": "Nemotron_01B0D4D4",
            "personaName": "Persona One",
            "status": "done",
            "phase": None,
            "appworldResult": {
                "taskId": "appworld-demo-personal-admin",
                "success": True,
                "score": 1.0,
                "outcome": "Calendar invite and email draft completed.",
                "reason": "The AppWorld task was completed with the expected API state.",
                "createdAt": "2026-06-29T00:00:00Z",
            },
            "trace": {
                "events": [
                    {
                        "step": 1,
                        "source": "agent",
                        "message": "Opened the AppWorld task state.",
                        "actions": [
                            {
                                "name": "appworld_api_call",
                                "arguments": {"app": "calendar", "method": "list_events"},
                            }
                        ],
                    }
                ],
                "raw": {"trajectory": [{"action": "list_events"}]},
            },
            "prompts": {
                "harborPrompt": "Persona prompt",
                "taskPrompt": "AppWorld task prompt",
            },
            "error": None,
        }

    def list_tasks(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "appworld-demo-personal-admin",
                "title": "AppWorld personal admin task",
                "appName": "AppWorld",
                "description": "Complete a task across AppWorld-style app APIs.",
                "outputArtifact": "appworld_result.json",
                "submissionProfile": "appworld_result",
            }
        ]

    def start(
        self,
        *,
        persona_id: str,
        task_id: str,
        persona_model: Optional[str],
        now,
    ) -> str:
        self.started.append(
            {
                "personaId": persona_id,
                "taskId": task_id,
                "personaModel": persona_model,
                "createdAt": now(),
            }
        )
        return "appworld_fake123"

    def view(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._view if job_id == "appworld_fake123" else None


@pytest.fixture()
def fake_appworld_eval(app):
    fake = _FakeAppWorldEvalService()
    app.state.services.appworld_eval = fake
    return fake


def test_list_appworld_eval_tasks(client, fake_appworld_eval):
    resp = client.get("/api/appworld-eval/tasks")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tasks"][0]["id"] == "appworld-demo-personal-admin"
    assert body["tasks"][0]["appName"] == "AppWorld"


def test_start_appworld_eval_returns_job_id(client, fake_appworld_eval):
    resp = client.post(
        "/api/appworld-eval",
        json={
            "personaId": "Nemotron_01B0D4D4",
            "taskId": "appworld-demo-personal-admin",
            "personaModel": "anthropic/claude-haiku-4-5",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"jobId": "appworld_fake123"}
    assert fake_appworld_eval.started[0]["personaId"] == "Nemotron_01B0D4D4"
    assert fake_appworld_eval.started[0]["taskId"] == "appworld-demo-personal-admin"
    assert fake_appworld_eval.started[0]["createdAt"].endswith("Z")


def test_get_appworld_eval_job_returns_result_trace_and_prompts(
    client, fake_appworld_eval
):
    resp = client.get("/api/appworld-eval/jobs/appworld_fake123")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["applicationType"] == "appworld"
    assert body["taskId"] == "appworld-demo-personal-admin"
    assert body["status"] == "done"
    assert body["appworldResult"]["success"] is True
    assert body["appworldResult"]["score"] == 1.0
    assert body["trace"]["events"][0]["actions"][0]["name"] == "appworld_api_call"
    assert body["prompts"]["taskPrompt"] == "AppWorld task prompt"


def test_get_appworld_eval_job_unknown_404(client, fake_appworld_eval):
    resp = client.get("/api/appworld-eval/jobs/appworld_missing")
    assert resp.status_code == 404
