"""Async service for local Playground web runs."""

from __future__ import annotations

import shutil
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import quote

from backend.service import run_store
from backend.service.config import persona_model as default_persona_model
from backend.service.web_types import WebEvalConfig, WebEvalResult, WebEvalTask

_WEB_RUN_LOCK = threading.Lock()


def _new_web_eval_id() -> str:
    return "web_" + uuid.uuid4().hex[:12]


def web_result_view(result: WebEvalResult) -> Dict[str, Any]:
    payload = result.to_dict()
    return {
        "task": payload["task"],
        "webResult": payload["webResult"],
        "trace": payload["trace"],
        "createdAt": payload["createdAt"],
        "prompts": payload["prompts"],
    }


def _trace_with_screenshot_urls(
    job_id: str,
    trace: Optional[Dict[str, Any]],
    *,
    local_screenshots: bool = False,
) -> Optional[Dict[str, Any]]:
    if trace is None:
        return None
    view = dict(trace)
    events: List[Dict[str, Any]] = []
    raw_events = trace.get("events")
    if isinstance(raw_events, list):
        for event in raw_events:
            if not isinstance(event, dict):
                continue
            event_view = dict(event)
            screenshot_file = event_view.get("screenshotFile")
            if event_view.get("screenshotUrl"):
                events.append(event_view)
                continue
            if local_screenshots and isinstance(screenshot_file, str) and screenshot_file:
                event_view["screenshotUrl"] = (
                    "/api/web-eval/jobs/{}/screenshots/{}".format(
                        job_id,
                        quote(screenshot_file, safe=""),
                    )
                )
            events.append(event_view)
    view["events"] = events
    return view


def _copy_screenshots(src_dir: Optional[Path], dst_dir: Path) -> None:
    """Copy a run's trace screenshots into a durable per-run dir (best-effort)."""
    if src_dir is None or not Path(src_dir).is_dir():
        return
    try:
        dst_dir.mkdir(parents=True, exist_ok=True)
        for screenshot in Path(src_dir).glob("screenshot_*"):
            if screenshot.suffix not in {".svg", ".webp"}:
                continue
            shutil.copy2(screenshot, dst_dir / screenshot.name)
    except Exception:  # noqa: BLE001 - best-effort
        return


@dataclass
class WebEvalProgress:
    job_id: str
    task: WebEvalTask
    persona_id: str
    persona_name: str
    status: str = "building"
    phase: Optional[str] = None
    web_result: Optional[Dict[str, Any]] = None
    trace: Optional[Dict[str, Any]] = None
    screenshots_dir: Optional[Path] = None
    prompts: Optional[Dict[str, str]] = None
    error: Optional[str] = None

    def to_view(self) -> Dict[str, Any]:
        return {
            "jobId": self.job_id,
            "applicationType": "web",
            "taskId": self.task.id,
            "taskTitle": self.task.title,
            "siteName": self.task.site_name,
            "siteUrl": self.task.site_url,
            "personaId": self.persona_id,
            "personaName": self.persona_name,
            "status": self.status,
            "phase": self.phase,
            "webResult": self.web_result,
            "trace": self.trace,
            "prompts": self.prompts,
            "error": self.error,
        }


class WebEvalService:
    """Start and poll local web runs for the Playground UI."""

    def __init__(
        self,
        *,
        get_persona: Callable[[str], Any],
        get_task: Callable[[str], WebEvalTask],
        list_tasks: Callable[[], List[WebEvalTask]],
        runner: Callable[..., WebEvalResult],
        runs_dir: Optional[Path] = None,
    ) -> None:
        self._get_persona = get_persona
        self._get_task = get_task
        self._list_tasks = list_tasks
        self._runner = runner
        self._runs_dir = runs_dir or run_store.default_runs_dir()
        self._guard = threading.Lock()
        self._progress: Dict[str, WebEvalProgress] = {}

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
        job_id = _new_web_eval_id()
        progress = WebEvalProgress(
            job_id=job_id,
            task=task,
            persona_id=persona_id,
            persona_name=getattr(persona, "name", persona_id),
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
            return progress.to_view() if progress else None

    def screenshot_path(self, job_id: str, filename: str) -> Path:
        safe_name = Path(filename).name
        if safe_name != filename or "/" in filename or "\\" in filename:
            raise ValueError("invalid screenshot filename")
        if not safe_name.startswith("screenshot_") or Path(safe_name).suffix not in {
            ".svg",
            ".webp",
        }:
            raise ValueError("invalid screenshot filename")
        with self._guard:
            progress = self._progress.get(job_id)
            screenshots_dir = progress.screenshots_dir if progress is not None else None
        if screenshots_dir is None:
            # Fall back to the durable per-run screenshots so a persisted web run
            # keeps its trace images after a restart (the in-memory job is gone).
            screenshots_dir = run_store.web_screenshots_dir(self._runs_dir, job_id)
        base = screenshots_dir.resolve()
        path = (screenshots_dir / safe_name).resolve()
        if path.parent != base or not path.is_file():
            raise FileNotFoundError(filename)
        return path

    def _run(
        self,
        progress: WebEvalProgress,
        persona: Any,
        task: WebEvalTask,
        persona_model: Optional[str],
        now: Callable[[], str],
    ) -> None:
        with _WEB_RUN_LOCK:
            try:
                config = WebEvalConfig(
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
                                progress.web_result = result.get("webResult")
                                progress.trace = _trace_with_screenshot_urls(
                                    progress.job_id,
                                    result.get("trace"),
                                )

                result = self._runner(
                    persona,
                    task,
                    config,
                    created_at=now(),
                    on_event=on_event,
                )
                result_view = web_result_view(result)
                web_result = result_view.get("webResult")
                has_local_screenshots = (
                    result.trace.screenshots_dir is not None
                    and result.trace.screenshots_dir.is_dir()
                )
                trace = _trace_with_screenshot_urls(
                    progress.job_id,
                    result_view.get("trace"),
                    local_screenshots=has_local_screenshots,
                )
                # Copy the trace screenshots to a durable per-run dir and persist
                # the run BEFORE marking done, so a "done" run is always already
                # saved and survives a restart. Both are best-effort.
                _copy_screenshots(
                    result.trace.screenshots_dir,
                    run_store.web_screenshots_dir(self._runs_dir, progress.job_id),
                )
                run_store.persist_run(
                    self._runs_dir,
                    {
                        "id": progress.job_id,
                        "applicationType": "web",
                        "createdAt": result_view.get("createdAt"),
                        "persona": run_store.persona_summary(persona),
                        "siteName": task.site_name,
                        "taskTitle": task.title,
                        "webResult": web_result,
                        "webTrace": trace,
                    },
                )
                with self._guard:
                    progress.web_result = web_result
                    progress.trace = trace
                    progress.screenshots_dir = (
                        result.trace.screenshots_dir if has_local_screenshots else None
                    )
                    progress.prompts = result_view.get("prompts")
                    progress.phase = None
                    progress.status = "done"
            except BaseException as exc:  # noqa: BLE001 - surface to client
                with self._guard:
                    progress.error = "{}: {}".format(type(exc).__name__, exc)
                    progress.status = "error"
