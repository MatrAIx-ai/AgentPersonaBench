"""Execute Harbor jobs on a remote runner worker."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path
from typing import Any, Callable, Sequence

_ALLOWED_REMOTE_HARBOR_ENV_KEYS = frozenset({"PYTHONPATH"})


def is_allowed_remote_harbor_env_key(key: str) -> bool:
    """Return True when ``key`` may cross the Remote Runner HTTP boundary."""
    return key in _ALLOWED_REMOTE_HARBOR_ENV_KEYS or key.startswith("MATRIX_")


def filter_remote_harbor_payload_env(env: dict[str, Any]) -> dict[str, str]:
    """Drop secrets and unrelated process env from a remote ``harbor_job`` payload."""
    return {
        str(key): str(value)
        for key, value in env.items()
        if is_allowed_remote_harbor_env_key(str(key))
    }


def resolve_repo_root(payload: dict[str, Any]) -> Path:
    raw = str(payload.get("repoRoot") or "").strip()
    if raw:
        return Path(raw).resolve()
    return Path.cwd().resolve()


def build_harbor_env(*, repo_root: Path, payload: dict[str, Any]) -> dict[str, str]:
    env = dict(os.environ)
    extra = payload.get("env")
    if isinstance(extra, dict):
        for key, value in filter_remote_harbor_payload_env(extra).items():
            env[key] = value
    existing = env.get("PYTHONPATH", "")
    path_entries = [entry for entry in existing.split(":") if entry]
    required_paths = [
        str(repo_root),
        str(repo_root / "src"),
        str(repo_root / "environment" / "runtime"),
        str(repo_root / "environment" / "agents"),
        str(repo_root / "packages" / "playground" / "src"),
        str(repo_root / "application" / "playground"),
    ]
    for path in reversed(required_paths):
        if path not in path_entries:
            path_entries.insert(0, path)
    env["PYTHONPATH"] = ":".join(path_entries)
    return env


def default_harbor_command() -> list[str]:
    override = os.environ.get("REMOTE_RUNNER_HARBOR_COMMAND", "").strip()
    if override:
        return shlex.split(override)
    from playground.harbor.playground import (
        _default_harbor_command,
    )

    return list(_default_harbor_command())


def write_incoming_job_config(
    *,
    repo_root: Path,
    job_name: str,
    config_yaml: str,
    runs_dir: Path | None = None,
) -> Path:
    base = runs_dir or (repo_root / "configs" / "jobs" / "remote-runner-incoming")
    base.mkdir(parents=True, exist_ok=True)
    safe_name = job_name.replace("/", "_").replace("\\", "_") or "remote-job"
    config_path = base / "{}.yaml".format(safe_name)
    config_path.write_text(config_yaml, encoding="utf-8")
    return config_path


def rel_config_path(config_path: Path, repo_root: Path) -> str:
    try:
        return str(config_path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(config_path.resolve())


def run_harbor_job(
    payload: dict[str, Any],
    *,
    command_runner: Callable[..., int] | None = None,
    harbor_command: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Materialize a Harbor job config and run ``harbor run`` on this worker."""
    config_yaml = str(payload.get("configYaml") or "").strip()
    if not config_yaml:
        raise ValueError("harbor_job payload requires configYaml")

    repo_root = resolve_repo_root(payload)
    job_name = str(payload.get("jobName") or "remote-job").strip() or "remote-job"
    config_path = write_incoming_job_config(
        repo_root=repo_root,
        job_name=job_name,
        config_yaml=config_yaml,
    )
    command = list(harbor_command or default_harbor_command()) + [
        "--yes",
        "-c",
        rel_config_path(config_path, repo_root),
    ]
    env = build_harbor_env(repo_root=repo_root, payload=payload)

    if command_runner is not None:
        exit_code = command_runner(command, cwd=repo_root, env=env)
    else:
        completed = subprocess.run(
            command,
            cwd=str(repo_root),
            env=env,
            check=False,
        )
        exit_code = int(completed.returncode)

    jobs_dir = str(payload.get("jobsDir") or "jobs")
    result = {
        "jobName": job_name,
        "configPath": rel_config_path(config_path, repo_root),
        "jobsDir": jobs_dir,
        "exitCode": exit_code,
    }
    if exit_code != 0:
        raise RuntimeError("harbor run exited with code {}".format(exit_code))
    return result
