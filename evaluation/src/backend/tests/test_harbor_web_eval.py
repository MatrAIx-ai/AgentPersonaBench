"""Tests for Harbor-backed web application eval helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from playground.harbor.web_eval import (
    HarborWebEvalConfig,
    HarborWebEvalRunner,
    WebEvalTask,
    build_result_from_harbor_web_artifacts,
    build_web_task_prompt,
)
from playground.types import Persona


def _task() -> WebEvalTask:
    return WebEvalTask(
        id="web-playwright-quote-choice",
        title="Quote choice",
        site_name="quotes.toscrape.com",
        site_url="https://quotes.toscrape.com/",
        task_path=Path("application/tasks/example-web-playwright_quote-choice"),
        description="Browse the quotes site and choose one quote to keep.",
        output_artifact="quote_choice.json",
        submission_profile="quote_choice",
    )


def _web_payload() -> dict:
    return {
        "selected_product_id": "desk-002",
        "selected_product_name": "FocusDesk Pro",
        "need_satisfaction": 8,
        "ease_of_use": 7,
        "overall_experience_rating": 8,
        "reason": "The comparison table made the tradeoffs clear for a remote-work desk choice.",
    }


def _trajectory() -> dict:
    return {
        "steps": [
            {
                "source": "agent",
                "message": "I will compare workspace products and choose one item.",
                "tool_calls": [
                    {
                        "function_name": "computer_action",
                        "arguments": {
                            "type": "navigate",
                            "url": "https://quotes.toscrape.com/",
                        },
                    }
                ],
                "observation": {
                    "results": [
                        {
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "media_type": "image/webp",
                                        "path": "screenshot_ep0.webp",
                                    },
                                }
                            ]
                        }
                    ]
                },
            },
            {
                "source": "agent",
                "message": "The desk with storage is the best fit.",
                "tool_calls": [
                    {
                        "function_name": "done",
                        "arguments": {"message": json.dumps(_web_payload())},
                    }
                ],
            },
        ]
    }


def test_build_web_task_prompt_requires_stated_operation_and_user_experience_feedback():
    prompt = build_web_task_prompt(_task())

    assert "Harbor supplies the persona system prompt" in prompt
    assert "Before using the site, state the concrete website task" in prompt
    assert "closed loop" in prompt
    assert "user experience" in prompt
    assert "collect" in prompt
    assert "quote_choice.json" in prompt
    assert "selected_product_id" in prompt


def test_build_result_from_harbor_web_artifacts_maps_result_and_trace(tmp_path):
    output_dir = tmp_path / "artifacts" / "app" / "output"
    output_dir.mkdir(parents=True)
    (output_dir / "quote_choice.json").write_text(
        json.dumps(_web_payload()),
        encoding="utf-8",
    )
    logs_dir = tmp_path / "logs" / "agent"
    logs_dir.mkdir(parents=True)
    (logs_dir / "trajectory.json").write_text(
        json.dumps(_trajectory()),
        encoding="utf-8",
    )

    result = build_result_from_harbor_web_artifacts(
        output_dir=output_dir,
        logs_dir=logs_dir,
        config=HarborWebEvalConfig(persona_model="anthropic/claude-sonnet-4-6"),
        persona=Persona(id="p1", name="Persona One", context="Careful shopper."),
        task=_task(),
        created_at="2026-06-24T00:00:00Z",
        prompts={"harborPrompt": "Careful shopper.", "taskPrompt": "Web task prompt."},
    )

    payload = result.to_dict()
    assert payload["config"]["personaModel"] == "anthropic/claude-sonnet-4-6"
    assert payload["task"]["id"] == "web-playwright-quote-choice"
    assert payload["webResult"] == {
        "selectedProductId": "desk-002",
        "selectedProductName": "FocusDesk Pro",
        "needSatisfaction": 8,
        "easeOfUse": 7,
        "overallExperienceRating": 8,
        "reason": "The comparison table made the tradeoffs clear for a remote-work desk choice.",
        "createdAt": "2026-06-24T00:00:00Z",
        "valid": True,
    }
    assert payload["trace"]["events"][0]["message"].startswith("I will compare")
    assert payload["trace"]["events"][0]["actions"][0]["name"] == "computer_action"
    assert payload["trace"]["events"][0]["screenshotFile"] == "screenshot_ep0.webp"
    assert payload["prompts"] == {
        "harborPrompt": "Careful shopper.",
        "taskPrompt": "Web task prompt.",
    }


def test_build_result_from_harbor_web_artifacts_rejects_bad_scores(tmp_path):
    output_dir = tmp_path / "artifacts" / "app" / "output"
    output_dir.mkdir(parents=True)
    payload = _web_payload()
    payload["need_satisfaction"] = True
    (output_dir / "quote_choice.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )
    logs_dir = tmp_path / "logs" / "agent"
    logs_dir.mkdir(parents=True)
    (logs_dir / "trajectory.json").write_text(
        json.dumps(_trajectory()),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="need_satisfaction"):
        build_result_from_harbor_web_artifacts(
            output_dir=output_dir,
            logs_dir=logs_dir,
            config=HarborWebEvalConfig(),
            persona=Persona(id="p1", name="Persona One"),
            task=_task(),
            created_at="2026-06-24T00:00:00Z",
        )


def test_harbor_web_runner_uses_ecommerce_task_without_harbor_submission_profile(
    tmp_path,
    monkeypatch,
):
    calls = []
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    (tmp_path / ".env.local").write_text(
        "ANTHROPIC_API_KEY=sk-test-anthropic\n",
        encoding="utf-8",
    )

    def fake_command(command, *, cwd, env):
        calls.append((command, cwd, env))
        config_path = command[command.index("-c") + 1]
        config = yaml.safe_load(open(config_path, encoding="utf-8"))
        assert config["agents"][0]["name"] == "persona-computer-1"
        assert "cua_submission_profile" not in config["agents"][0]["kwargs"]
        assert config["tasks"][0]["path"].endswith(
            "application/tasks/example-web-playwright_quote-choice"
        )
        assert config["environment"]["force_build"] is False
        job_name = config["job_name"]
        output_dir = (
            Path(config["jobs_dir"])
            / job_name
            / "trial_1"
            / "artifacts"
            / "app"
            / "output"
        )
        output_dir.mkdir(parents=True)
        (output_dir / "quote_choice.json").write_text(
            json.dumps(_web_payload()),
            encoding="utf-8",
        )
        logs_dir = Path(config["jobs_dir"]) / job_name / "trial_1" / "agent"
        logs_dir.mkdir(parents=True)
        (logs_dir / "trajectory.json").write_text(
            json.dumps(_trajectory()),
            encoding="utf-8",
        )
        return 0

    runner = HarborWebEvalRunner(
        repo_root=tmp_path,
        runs_root=tmp_path / "runs",
        command_runner=fake_command,
        harbor_command=("harbor", "run"),
    )
    result = runner(
        Persona(id="p1", name="Persona One", context="Careful shopper."),
        _task(),
        HarborWebEvalConfig(persona_model="anthropic/claude-haiku-4-5"),
        created_at="2026-06-24T00:00:00Z",
    )

    assert calls
    assert calls[0][2]["ANTHROPIC_API_KEY"] == "sk-test-anthropic"
    assert result.web_result.selected_product_id == "desk-002"
    assert result.trace.events[0]["message"].startswith("I will compare")


def test_harbor_web_runner_recovers_submission_from_final_answer_when_artifact_missing(
    tmp_path,
):
    (tmp_path / ".env.local").write_text(
        "ANTHROPIC_API_KEY=sk-test-anthropic\n",
        encoding="utf-8",
    )

    def fake_command(command, *, cwd, env):
        config_path = command[command.index("-c") + 1]
        config = yaml.safe_load(open(config_path, encoding="utf-8"))
        job_name = config["job_name"]
        output_dir = (
            Path(config["jobs_dir"])
            / job_name
            / "trial_1"
            / "artifacts"
            / "app"
            / "output"
        )
        output_dir.mkdir(parents=True)
        logs_dir = Path(config["jobs_dir"]) / job_name / "trial_1" / "agent"
        logs_dir.mkdir(parents=True)
        (logs_dir / "trajectory.json").write_text(
            json.dumps(
                {
                    "steps": [
                        {
                            "source": "agent",
                            "message": "I used the website and picked a desk.",
                            "tool_calls": [
                                {
                                    "function_name": "mark_task_complete",
                                    "arguments": {"result": None},
                                }
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        (logs_dir / "final_answer.txt").write_text(
            "Final submission:\n```json\n{}\n```".format(
                json.dumps(_web_payload())
            ),
            encoding="utf-8",
        )
        return 0

    runner = HarborWebEvalRunner(
        repo_root=tmp_path,
        runs_root=tmp_path / "runs",
        command_runner=fake_command,
        harbor_command=("harbor", "run"),
    )
    result = runner(
        Persona(id="p1", name="Persona One", context="Careful shopper."),
        _task(),
        HarborWebEvalConfig(persona_model="anthropic/claude-haiku-4-5"),
        created_at="2026-06-24T00:00:00Z",
    )

    assert result.web_result.selected_product_id == "desk-002"
    artifact = next((tmp_path / "runs").rglob("quote_choice.json"))
    assert json.loads(artifact.read_text(encoding="utf-8")) == _web_payload()
