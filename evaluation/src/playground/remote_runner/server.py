"""General remote runner HTTP service for Playground.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from playground.remote_runner.dispatch import run_harbor_job

__all__ = ["create_app"]

_TERMINAL_STATUSES = {"succeeded", "failed"}
_HARBOR_JOB_TYPES = frozenset({"harbor_job", "harbor"})
_LEGACY_WEB_TYPES = frozenset({"web"})


class CreateRunRequest(BaseModel):
    task_type: str = Field(alias="taskType")
    payload: dict[str, Any] = Field(default_factory=dict)


@dataclass
class RemoteRunnerRun:
    id: str
    task_type: str
    payload: dict[str, Any]
    output_dir: Path
    status: str = "queued"
    error: str | None = None
    artifacts: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "id": self.id,
            "status": self.status,
            "taskType": self.task_type,
        }
        if self.error:
            data["error"] = self.error
        return data


class RemoteRunnerStore:
    def __init__(self, runs_dir: Path) -> None:
        self.runs_dir = runs_dir
        self._lock = threading.Lock()
        self._runs: dict[str, RemoteRunnerRun] = {}

    def create(self, task_type: str, payload: dict[str, Any]) -> RemoteRunnerRun:
        run_id = "run_" + uuid.uuid4().hex[:12]
        run = RemoteRunnerRun(
            id=run_id,
            task_type=task_type,
            payload=dict(payload),
            output_dir=self.runs_dir / run_id,
        )
        with self._lock:
            self._runs[run_id] = run
        return run

    def get(self, run_id: str) -> RemoteRunnerRun | None:
        with self._lock:
            return self._runs.get(run_id)

    def update(self, run: RemoteRunnerRun, **changes: Any) -> None:
        with self._lock:
            for key, value in changes.items():
                setattr(run, key, value)


def create_app(*, runs_dir: Path | None = None) -> FastAPI:
    """Return a FastAPI app exposing the general remote runner API."""
    store = RemoteRunnerStore(
        Path(runs_dir)
        if runs_dir is not None
        else Path(tempfile.gettempdir()) / "matraix-remote-runner"
    )
    app = FastAPI(title="MatrAIx Remote Runner", version="0.1")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "remote-runner"}

    @app.post("/v1/runs")
    def create_run(body: CreateRunRequest) -> dict[str, Any]:
        run = store.create(body.task_type, body.payload)
        if _run_inline():
            _execute_run(store, run)
        else:
            thread = threading.Thread(
                target=_execute_run,
                args=(store, run),
                daemon=True,
            )
            thread.start()
        return run.to_dict()

    @app.get("/v1/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, Any]:
        run = store.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        return run.to_dict()

    @app.get("/v1/runs/{run_id}/artifacts/{name:path}")
    def get_artifact(run_id: str, name: str) -> JSONResponse:
        run = store.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        if run.status not in _TERMINAL_STATUSES:
            raise HTTPException(status_code=409, detail="run not finished")
        if run.status == "failed":
            raise HTTPException(status_code=500, detail=run.error or "run failed")
        artifact = _artifact(run, name)
        return JSONResponse(artifact)

    @app.get("/mock/{run_id}/{filename}")
    def mock_screenshot(run_id: str, filename: str) -> Response:
        run = store.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        if filename not in {"step-1.svg", "step-2.svg"}:
            raise HTTPException(status_code=404, detail="mock screenshot not found")
        label = "Opened site" if filename == "step-1.svg" else "Selected product"
        return Response(_mock_svg(label), media_type="image/svg+xml")

    return app


def _run_inline() -> bool:
    raw = os.environ.get("REMOTE_RUNNER_INLINE", "0")
    return raw.lower() in {"1", "true", "yes"}


def _execute_run(store: RemoteRunnerStore, run: RemoteRunnerRun) -> None:
    store.update(run, status="running")
    try:
        if run.task_type in _HARBOR_JOB_TYPES:
            artifacts = _run_harbor_job(run)
        elif run.task_type in _LEGACY_WEB_TYPES:
            command = _legacy_web_command()
            if command:
                artifacts = _run_command(run, command)
            else:
                artifacts = _mock_web_artifacts(run)
        else:
            raise ValueError(
                "unsupported taskType {!r}; use harbor_job for general Harbor dispatch".format(
                    run.task_type
                )
            )
        store.update(run, status="succeeded", artifacts=artifacts)
    except Exception as exc:  # noqa: BLE001 - surfaced through run status
        store.update(run, status="failed", error="{}: {}".format(type(exc).__name__, exc))


def _run_harbor_job(run: RemoteRunnerRun) -> dict[str, Any]:
    run.output_dir.mkdir(parents=True, exist_ok=True)
    payload_path = run.output_dir / "payload.json"
    payload_path.write_text(json.dumps(run.payload, indent=2), encoding="utf-8")
    result = run_harbor_job(run.payload)
    result_path = run.output_dir / "harbor_job_result.json"
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return {"harbor_job_result.json": result, **result}


def _legacy_web_command() -> str:
    return os.environ.get("REMOTE_RUNNER_WEB_COMMAND", "").strip()


def _run_command(run: RemoteRunnerRun, command: str) -> dict[str, Any]:
    run.output_dir.mkdir(parents=True, exist_ok=True)
    payload_path = run.output_dir / "payload.json"
    payload_path.write_text(json.dumps(run.payload, indent=2), encoding="utf-8")
    env = {
        **os.environ,
        "REMOTE_RUNNER_RUN_ID": run.id,
        "REMOTE_RUNNER_TASK_TYPE": run.task_type,
        "REMOTE_RUNNER_PAYLOAD_JSON": str(payload_path),
        "REMOTE_RUNNER_OUTPUT_DIR": str(run.output_dir),
    }
    timeout = float(os.environ.get("REMOTE_RUNNER_COMMAND_TIMEOUT", "1800"))
    completed = subprocess.run(
        command,
        cwd=str(Path.cwd()),
        env=env,
        shell=True,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "command exited {}: {}".format(
                completed.returncode,
                (completed.stderr or completed.stdout or "").strip()[:1000],
            )
        )
    return _load_web_output_artifacts(run.output_dir)


def _load_web_output_artifacts(output_dir: Path) -> dict[str, Any]:
    artifacts: dict[str, Any] = {}
    for path in output_dir.iterdir() if output_dir.is_dir() else []:
        if not path.is_file():
            continue
        if path.suffix == ".json":
            artifacts[path.name] = json.loads(path.read_text(encoding="utf-8"))
        elif path.name == "screenshots_dir":
            artifacts[path.name] = path.read_text(encoding="utf-8").strip()
    if "trace.json" not in artifacts:
        raise ValueError("command did not produce trace.json")
    if "web_result.json" not in artifacts:
        raise ValueError("command did not produce a web result JSON artifact")
    return artifacts


def _mock_web_artifacts(run: RemoteRunnerRun) -> dict[str, Any]:
    task = run.payload.get("task") if isinstance(run.payload, dict) else {}
    task = task if isinstance(task, dict) else {}
    output_artifact = str(task.get("outputArtifact") or "web_result.json")
    web_result = {
        "selected_product_id": "remote-runner-demo-product",
        "selected_product_name": "Remote Runner Demo Product",
        "need_satisfaction": 8,
        "ease_of_use": 8,
        "information_quality": 8,
        "overall_experience_rating": 8,
        "reason": "The remote runner completed a deterministic web mock run.",
    }
    trace = {
        "events": [
            {
                "step": 1,
                "source": "agent",
                "message": "Opened the ecommerce task site.",
            },
            {
                "step": 2,
                "source": "agent",
                "message": "Selected a product and submitted the final answer.",
            },
        ],
        "raw": {"remoteRunId": run.id, "mode": "mock"},
    }
    return {
        output_artifact: dict(web_result),
        "web_result.json": dict(web_result),
        "trace.json": trace,
    }


def _artifact(run: RemoteRunnerRun, name: str) -> Any:
    if name in run.artifacts:
        return run.artifacts[name]
    path = run.output_dir / Path(name).name
    if path.is_file() and path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    raise HTTPException(status_code=404, detail="artifact not found")


def _mock_svg(label: str) -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">
  <rect width="640" height="360" fill="#102033"/>
  <rect x="48" y="52" width="544" height="256" rx="14" fill="#f7fafc"/>
  <text x="72" y="104" font-family="Arial, sans-serif" font-size="28" fill="#172033">Remote runner mock</text>
  <text x="72" y="152" font-family="Arial, sans-serif" font-size="22" fill="#405166">{}</text>
</svg>""".format(label)


app = create_app()
