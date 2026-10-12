"""Tests for the general remote runner HTTP service."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from playground.remote_runner.dispatch import run_harbor_job
from playground.remote_runner.server import create_app


def test_remote_runner_server_harbor_job(tmp_path, monkeypatch) -> None:
    calls: list[list[str]] = []

    def _fake_harbor(payload, *, command_runner=None, harbor_command=None):
        del harbor_command

        def _runner(command, *, cwd, env):
            calls.append(list(command))
            return 0

        return run_harbor_job(payload, command_runner=_runner)

    from playground import remote_runner

    monkeypatch.setattr(remote_runner.server, "run_harbor_job", _fake_harbor)
    monkeypatch.setenv("REMOTE_RUNNER_INLINE", "1")

    client = TestClient(create_app(runs_dir=tmp_path / "runs"))
    response = client.post(
        "/v1/runs",
        json={
            "taskType": "harbor_job",
            "payload": {
                "jobName": "demo",
                "configYaml": "job_name: demo\n",
                "repoRoot": str(tmp_path),
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"

    run_id = body["id"]
    artifact = client.get("/v1/runs/{}/artifacts/harbor_job_result.json".format(run_id))
    assert artifact.status_code == 200
    assert artifact.json()["jobName"] == "demo"
    assert calls


def test_remote_runner_server_rejects_unknown_task_type(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("REMOTE_RUNNER_INLINE", "1")
    client = TestClient(create_app(runs_dir=tmp_path / "runs"))
    response = client.post(
        "/v1/runs",
        json={"taskType": "survey", "payload": {}},
    )
    assert response.status_code == 200
    run_id = response.json()["id"]
    detail = client.get("/v1/runs/{}".format(run_id)).json()
    assert detail["status"] == "failed"
