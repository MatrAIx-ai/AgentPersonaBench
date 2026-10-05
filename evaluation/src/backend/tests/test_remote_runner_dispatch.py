"""Tests for remote runner Harbor dispatch helpers."""

from __future__ import annotations

from playground.remote_runner.dispatch import (
    filter_remote_harbor_payload_env,
    run_harbor_job,
    write_incoming_job_config,
)


def test_write_incoming_job_config(tmp_path) -> None:
    path = write_incoming_job_config(
        repo_root=tmp_path,
        job_name="demo-job",
        config_yaml="job_name: demo-job\n",
    )
    assert path.is_file()
    assert "demo-job" in path.name


def test_run_harbor_job_invokes_command_runner(tmp_path, monkeypatch) -> None:
    calls: list[dict] = []

    def _fake_runner(command, *, cwd, env):
        calls.append({"command": list(command), "cwd": cwd, "env": env})
        return 0

    monkeypatch.setenv("REMOTE_RUNNER_HARBOR_COMMAND", "echo harbor")

    result = run_harbor_job(
        {
            "jobName": "demo-job",
            "configYaml": "job_name: demo-job\n",
            "repoRoot": str(tmp_path),
            "jobsDir": "jobs",
            "env": {"MATRIX_SURVEY_TASK_PATH": "application/tasks/survey_product-attitudes"},
        },
        command_runner=_fake_runner,
    )

    assert result["exitCode"] == 0
    assert calls
    assert calls[0]["command"][:2] == ["echo", "harbor"]
    assert "--yes" in calls[0]["command"]
    assert calls[0]["env"]["MATRIX_SURVEY_TASK_PATH"] == "application/tasks/survey_product-attitudes"
    pythonpath = calls[0]["env"]["PYTHONPATH"].split(":")
    assert str(tmp_path) in pythonpath
    assert str(tmp_path / "src") in pythonpath
    assert str(tmp_path / "environment" / "runtime") in pythonpath
    assert str(tmp_path / "environment" / "agents") in pythonpath
    assert str(tmp_path / "packages" / "playground" / "src") in pythonpath
    assert str(tmp_path / "application" / "playground") in pythonpath


def test_filter_remote_harbor_payload_env_drops_secrets() -> None:
    filtered = filter_remote_harbor_payload_env(
        {
            "PYTHONPATH": "/repo",
            "MATRIX_SURVEY_TASK_PATH": "application/tasks/demo",
            "ANTHROPIC_API_KEY": "sk-ant-secret",
            "HOME": "/Users/demo",
        }
    )
    assert filtered == {
        "PYTHONPATH": "/repo",
        "MATRIX_SURVEY_TASK_PATH": "application/tasks/demo",
    }


def test_run_harbor_job_ignores_secret_payload_env(tmp_path, monkeypatch) -> None:
    calls: list[dict] = []

    def _fake_runner(command, *, cwd, env):
        calls.append({"command": list(command), "cwd": cwd, "env": env})
        return 0

    monkeypatch.setenv("REMOTE_RUNNER_HARBOR_COMMAND", "echo harbor")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "worker-local-key")

    run_harbor_job(
        {
            "jobName": "demo-job",
            "configYaml": "job_name: demo-job\n",
            "repoRoot": str(tmp_path),
            "jobsDir": "jobs",
            "env": {
                "MATRIX_SURVEY_TASK_PATH": "application/tasks/survey_product-attitudes",
                "ANTHROPIC_API_KEY": "attacker-injected-key",
            },
        },
        command_runner=_fake_runner,
    )

    assert calls[0]["env"]["ANTHROPIC_API_KEY"] == "worker-local-key"
    assert calls[0]["env"]["MATRIX_SURVEY_TASK_PATH"] == "application/tasks/survey_product-attitudes"
