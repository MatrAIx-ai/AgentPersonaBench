import json

from backend.service.harbor_job_service import HarborJobService
from playground.post_run_feedback import (
    maybe_write_trial_user_feedback,
)


class _FakeJSONClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def complete_json(self, system, user):
        self.calls.append((system, user))
        return dict(self.payload)


def _write_task(repo, rel_path: str, *, metadata_type: str, schema_text: str | None):
    task_dir = repo / rel_path
    input_dir = task_dir / "input"
    input_dir.mkdir(parents=True)
    (task_dir / "task.toml").write_text(
        '[metadata]\ntype = "{}"\n'.format(metadata_type),
        encoding="utf-8",
    )
    (task_dir / "instruction.md").write_text(
        "# Instruction\nComplete the task realistically.",
        encoding="utf-8",
    )
    if schema_text is not None:
        (input_dir / "self_report_schema.yaml").write_text(schema_text, encoding="utf-8")
    return task_dir


def _write_trial(repo, *, task_path: str):
    trial_dir = repo / "jobs" / "demo-job" / "trial-a"
    output_dir = trial_dir / "artifacts" / "app" / "output"
    output_dir.mkdir(parents=True)
    (trial_dir / "agent").mkdir()
    persona_rel = "persona/datasets/matraix-persona-dev-sample/persona_0001.yaml"
    persona_path = repo / persona_rel
    persona_path.parent.mkdir(parents=True, exist_ok=True)
    persona_path.write_text(
        "persona_id: '0001'\ndisplay_name: Persona One\nsystem_prompt: Budget-conscious and careful.\n",
        encoding="utf-8",
    )
    (trial_dir / "config.json").write_text(
        json.dumps(
            {
                "task": {"path": task_path},
                "agent": {
                    "model_name": "openai/gpt-4o-mini",
                    "kwargs": {"persona_path": persona_rel},
                },
            }
        ),
        encoding="utf-8",
    )
    (trial_dir / "agent" / "trajectory.json").write_text(
        json.dumps(
            {
                "steps": [
                    {
                        "source": "agent",
                        "message": "Opened the app, reviewed the choices, and completed the task.",
                        "tool_calls": [{"function_name": "browser_navigate", "arguments": {}}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return trial_dir, output_dir


def test_maybe_write_trial_user_feedback_for_web(monkeypatch, tmp_path):
    repo = tmp_path
    _write_task(
        repo,
        "application/tasks/example-web-playwright_quote-choice",
        metadata_type="web",
        schema_text="""
artifactName: user_feedback.json
fields:
  - key: satisfaction
    kind: integer
    prompt: How satisfied were you?
    minimum: 1
    maximum: 5
    required: true
""".strip(),
    )
    trial_dir, output_dir = _write_trial(
        repo,
        task_path="application/tasks/example-web-playwright_quote-choice",
    )
    (output_dir / "quote_choice.json").write_text(
        json.dumps({"selectedProductId": "lamp-1", "selectedProductName": "Lamp One"}),
        encoding="utf-8",
    )
    client = _FakeJSONClient({"satisfaction": 4})
    monkeypatch.setattr(
        "playground.post_run_feedback.build_json_client",
        lambda model, temperature=0.1: client,
    )

    path = maybe_write_trial_user_feedback(repo_root=repo, trial_dir=trial_dir)

    assert path == output_dir / "user_feedback.json"
    assert json.loads(path.read_text(encoding="utf-8")) == {"satisfaction": 4}
    assert client.calls
    assert "quote_choice.json" in client.calls[0][1]


def test_maybe_write_trial_user_feedback_for_os_app(monkeypatch, tmp_path):
    repo = tmp_path
    _write_task(
        repo,
        "application/tasks/example-computer-use-ios_photo-access-review",
        metadata_type="mobile",
        schema_text="""
artifactName: user_feedback.json
fields:
  - key: confidence
    kind: integer
    prompt: How confident do you feel about the outcome?
    minimum: 1
    maximum: 5
    required: true
""".strip(),
    )
    trial_dir, output_dir = _write_trial(
        repo,
        task_path="application/tasks/example-computer-use-ios_photo-access-review",
    )
    (output_dir / "decision.json").write_text(
        json.dumps({"allowPhotos": False, "reason": "Too much access requested."}),
        encoding="utf-8",
    )
    client = _FakeJSONClient({"confidence": 5})
    monkeypatch.setattr(
        "playground.post_run_feedback.build_json_client",
        lambda model, temperature=0.1: client,
    )

    path = maybe_write_trial_user_feedback(repo_root=repo, trial_dir=trial_dir)

    assert path == output_dir / "user_feedback.json"
    assert json.loads(path.read_text(encoding="utf-8")) == {"confidence": 5}
    assert client.calls
    assert "decision.json" in client.calls[0][1]


def test_harbor_job_service_calls_post_run_feedback(tmp_path, monkeypatch):
    repo = tmp_path
    job_dir = repo / "jobs" / "demo-job"
    trial_dir = job_dir / "trial-a"
    trial_dir.mkdir(parents=True)
    (trial_dir / "config.json").write_text("{}", encoding="utf-8")
    calls = []
    monkeypatch.setattr(
        "playground.post_run_feedback.maybe_write_trial_user_feedback",
        lambda *, repo_root, trial_dir: calls.append((repo_root, trial_dir)),
    )
    service = HarborJobService(
        repo_root=repo,
        jobs_dir=repo / "jobs",
        generated_configs_dir=repo / "configs" / "jobs",
    )

    service._maybe_generate_post_run_feedback("demo-job")

    assert calls == [(repo, trial_dir)]
    service.shutdown()
