"""API contract tests for Playground web application runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("pydantic")


class _FakeWebEvalService:
    def __init__(self, screenshot_dir: Path) -> None:
        self.started: list[dict[str, Any]] = []
        self._screenshot_dir = screenshot_dir
        self._screenshot_dir.mkdir(parents=True, exist_ok=True)
        (self._screenshot_dir / "screenshot_ep0.webp").write_bytes(b"webp-image")
        (self._screenshot_dir / "screenshot_001.svg").write_text(
            "<svg xmlns='http://www.w3.org/2000/svg'></svg>",
            encoding="utf-8",
        )
        self._view: Dict[str, Any] = {
            "jobId": "web_fake123",
            "applicationType": "web",
            "taskId": "example-web-playwright-quote-choice",
            "taskTitle": "Quote choice",
            "siteName": "quotes.toscrape.com",
            "siteUrl": "https://quotes.toscrape.com/",
            "personaId": "Nemotron_01B0D4D4",
            "personaName": "Persona One",
            "status": "done",
            "phase": None,
            "webResult": {
                "selectedProductId": "quote-42",
                "selectedProductName": "Famous quote",
                "needSatisfaction": 8,
                "easeOfUse": 7,
                "overallExperienceRating": 8,
                "reason": "The shortlist matched the assigned preference.",
                "createdAt": "2026-06-24T00:00:00Z",
                "valid": True,
            },
            "trace": {
                "events": [
                    {
                        "step": 1,
                        "source": "agent",
                        "message": "I will browse quotes and choose one.",
                        "screenshotFile": "screenshot_ep0.webp",
                        "screenshotUrl": (
                            "/api/web-eval/jobs/web_fake123/screenshots/"
                            "screenshot_ep0.webp"
                        ),
                        "actions": [
                            {
                                "name": "navigate",
                                "arguments": {"url": "https://quotes.toscrape.com/"},
                            }
                        ],
                    }
                ],
                "raw": {
                    "steps": [
                        {
                            "source": "agent",
                            "message": "I will browse quotes and choose one.",
                        }
                    ]
                },
            },
            "prompts": {
                "harborPrompt": "Persona prompt",
                "taskPrompt": "Web task prompt",
            },
            "error": None,
        }

    def list_tasks(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "example-web-playwright-quote-choice",
                "title": "Quote choice",
                "siteName": "quotes.toscrape.com",
                "siteUrl": "https://quotes.toscrape.com/",
                "description": "Browse quotes and report a preference.",
                "outputArtifact": "quote_choice.json",
                "submissionProfile": "quote_choice",
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
        return "web_fake123"

    def view(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._view if job_id == "web_fake123" else None

    def screenshot_path(self, job_id: str, filename: str) -> Path:
        if job_id != "web_fake123":
            raise KeyError(job_id)
        if "\\" in filename or "/" in filename:
            raise ValueError("invalid screenshot filename")
        if filename not in {"screenshot_ep0.webp", "screenshot_001.svg"}:
            raise FileNotFoundError(filename)
        return self._screenshot_dir / filename


@pytest.fixture()
def fake_web_eval(app, tmp_path):
    fake = _FakeWebEvalService(tmp_path / "screenshots")
    app.state.services.web_eval = fake
    return fake


def test_list_web_eval_tasks(client, fake_web_eval):
    resp = client.get("/api/web-eval/tasks")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tasks"][0]["id"] == "example-web-playwright-quote-choice"
    assert body["tasks"][0]["siteName"] == "quotes.toscrape.com"


def test_start_web_eval_returns_job_id(client, fake_web_eval):
    resp = client.post(
        "/api/web-eval",
        json={
            "personaId": "Nemotron_01B0D4D4",
            "taskId": "example-web-playwright-quote-choice",
            "personaModel": "anthropic/claude-haiku-4-5",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"jobId": "web_fake123"}
    assert fake_web_eval.started == [
        {
            "personaId": "Nemotron_01B0D4D4",
            "taskId": "example-web-playwright-quote-choice",
            "personaModel": "anthropic/claude-haiku-4-5",
            "createdAt": fake_web_eval.started[0]["createdAt"],
        }
    ]
    assert fake_web_eval.started[0]["createdAt"].endswith("Z")


def test_get_web_eval_job_returns_result_trace_and_prompts(client, fake_web_eval):
    resp = client.get("/api/web-eval/jobs/web_fake123")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["applicationType"] == "web"
    assert body["taskId"] == "example-web-playwright-quote-choice"
    assert body["status"] == "done"
    assert body["webResult"]["selectedProductId"] == "quote-42"
    assert body["webResult"]["needSatisfaction"] == 8
    assert body["trace"]["events"][0]["actions"][0]["name"] == "navigate"
    assert body["trace"]["events"][0]["screenshotFile"] == "screenshot_ep0.webp"
    assert body["trace"]["events"][0]["screenshotUrl"].endswith(
        "/api/web-eval/jobs/web_fake123/screenshots/screenshot_ep0.webp"
    )
    assert body["prompts"]["taskPrompt"] == "Web task prompt"


def test_get_web_eval_job_unknown_404(client, fake_web_eval):
    resp = client.get("/api/web-eval/jobs/web_missing")
    assert resp.status_code == 404


def test_get_web_eval_screenshot_returns_webp(client, fake_web_eval):
    resp = client.get(
        "/api/web-eval/jobs/web_fake123/screenshots/screenshot_ep0.webp"
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "image/webp"
    assert resp.content == b"webp-image"


def test_get_web_eval_screenshot_returns_svg(client, fake_web_eval):
    resp = client.get(
        "/api/web-eval/jobs/web_fake123/screenshots/screenshot_001.svg"
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "image/svg+xml"
    assert resp.text.startswith("<svg")


def test_get_web_eval_screenshot_rejects_path_traversal(client, fake_web_eval):
    resp = client.get("/api/web-eval/jobs/web_fake123/screenshots/..%5Csecret.webp")
    assert resp.status_code == 400
