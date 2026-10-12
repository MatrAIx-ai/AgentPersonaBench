"""Async service for Playground AppWorld runs."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from backend.service import run_store
from backend.service.appworld_types import (
    AppWorldEvalConfig,
    AppWorldEvalResult,
    AppWorldEvalTask,
)
from backend.service.config import persona_model as default_persona_model


def _new_appworld_eval_id() -> str:
    return "appworld_" + uuid.uuid4().hex[:12]


def appworld_result_view(result: AppWorldEvalResult) -> Dict[str, Any]:
    payload = result.to_dict()
    return {
        "task": payload["task"],
        "appworldResult": payload["appworldResult"],
        "trace": payload["trace"],
        "createdAt": payload["createdAt"],
        "prompts": payload["prompts"],
    }


@dataclass
class AppWorldEvalProgress:
    job_id: str
    task: AppWorldEvalTask
    persona_id: str
    persona_name: str
    status: str = "building"
    phase: Optional[str] = None
    appworld_result: Optional[Dict[str, Any]] = None
    trace: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, str]] = None
    error: Optional[str] = None

    def to_view(self) -> Dict[str, Any]:
        return {
            "jobId": self.job_id,
            "applicationType": "appworld",
            "taskId": self.task.id,
            "taskTitle": self.task.title,
            "appName": self.task.app_name,
            "personaId": self.persona_id,
            "personaName": self.persona_name,
            "status": self.status,
            "phase": self.phase,
            "appworldResult": self.appworld_result,
            "trace": self.trace,
            "prompts": self.prompts,
            "error": self.error,
        }


class AppWorldEvalService:
    """Start and poll AppWorld runs for the Playground UI."""

    def __init__(
        self,
        *,
        get_persona: Callable[[str], Any],
        get_task: Callable[[str], AppWorldEvalTask],
        list_tasks: Callable[[], List[AppWorldEvalTask]],
        runner: Callable[..., AppWorldEvalResult],
        runs_dir: Optional[Path] = None,
    ) -> None:
        self._get_persona = get_persona
        self._get_task = get_task
        self._list_tasks = list_tasks
        self._runner = runner
        self._runs_dir = runs_dir or run_store.default_runs_dir()
        self._guard = threading.Lock()
        self._progress: Dict[str, AppWorldEvalProgress] = {}

    def list_tasks(self) -> List[Dict[str, Any]]:
        return [task.to_dict() for task in self._list_tasks()]

    def start(
        self,
        *,
        persona_id: str,
        task_id: str,
        persona_model: Optional[str],
        now: Callable[[], str],
    ) -> str:
        persona = self._get_persona(persona_id)
        task = self._get_task(task_id)
        job_id = _new_appworld_eval_id()
        progress = AppWorldEvalProgress(
            job_id=job_id,
            task=task,
            persona_id=persona_id,
            persona_name=run_store.friendly_persona_name(persona),
        )
        with self._guard:
            self._progress[job_id] = progress
        thread = threading.Thread(
            target=self._run,
            args=(progress, persona, task, persona_model, now),
            daemon=True,
        )
        thread.start()
        return job_id

    def view(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._guard:
            progress = self._progress.get(job_id)
            if progress is not None:
                return progress.to_view()
        record = run_store.load_run(self._runs_dir, job_id)
        if record is None or record.get("applicationType") != "appworld":
            return None
        return {
            "jobId": record.get("id"),
            "applicationType": "appworld",
            "taskId": record.get("taskId"),
            "taskTitle": record.get("taskTitle"),
            "appName": record.get("appName"),
            "personaId": (record.get("persona") or {}).get("id"),
            "personaName": run_store.friendly_persona_name(record.get("persona") or {}),
            "status": "done",
            "phase": None,
            "appworldResult": record.get("appworldResult"),
            "trace": record.get("appworldTrace"),
            "prompts": record.get("prompts"),
            "error": None,
        }

    def _run(
        self,
        progress: AppWorldEvalProgress,
        persona: Any,
        task: AppWorldEvalTask,
        persona_model: Optional[str],
        now: Callable[[], str],
    ) -> None:
        try:
            config = AppWorldEvalConfig(
                persona_model=persona_model or default_persona_model(),
            )
            with self._guard:
                progress.status = "running"

            def on_event(event: Dict[str, Any]) -> None:
                etype = event.get("type")
                if etype == "phase":
                    with self._guard:
                        progress.phase = str(event.get("phase") or "")
                elif etype == "prompts":
                    prompts = event.get("prompts")
                    if isinstance(prompts, dict):
                        with self._guard:
                            progress.prompts = {
                                str(key): str(value)
                                for key, value in prompts.items()
                                if value is not None
                            }
                elif etype == "done":
                    result = event.get("result")
                    if isinstance(result, dict):
                        with self._guard:
                            progress.appworld_result = result.get("appworldResult")
                            progress.trace = result.get("trace")

            result = self._runner(
                persona,
                task,
                config,
                created_at=now(),
                on_event=on_event,
            )
            result_view = appworld_result_view(result)
            appworld_result = result_view.get("appworldResult")
            trace = result_view.get("trace")
            run_store.persist_run(
                self._runs_dir,
                {
                    "id": progress.job_id,
                    "applicationType": "appworld",
                    "createdAt": result_view.get("createdAt"),
                    "persona": run_store.persona_summary(persona),
                    "taskId": task.id,
                    "taskTitle": task.title,
                    "appName": task.app_name,
                    "appworldResult": appworld_result,
                    "appworldTrace": trace,
                    "prompts": result_view.get("prompts"),
                },
            )
            with self._guard:
                progress.appworld_result = appworld_result
                progress.trace = trace
                progress.prompts = result_view.get("prompts")
                progress.phase = None
                progress.status = "done"
        except BaseException as exc:  # noqa: BLE001 - surface to client
            with self._guard:
                progress.error = "{}: {}".format(type(exc).__name__, exc)
                progress.status = "error"
