"""Run a playground as a background job with live progress.

Playground execution is serialized process-globally (`_RUN_LOCK`) because the
underlying recommender resources and process-level environment are expensive and
partly shared across runs.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
import inspect
from typing import Any, Callable, Dict, List, Optional

from backend.service import run_store
from playground.runner import run_playground as _default_runner
from playground.types import DEFAULT_PERSONA_MODEL, PlaygroundConfig

_RUN_LOCK = threading.Lock()


def _new_playground_id() -> str:
    import uuid

    return "wt_" + uuid.uuid4().hex[:12]


def _default_runs_dir() -> Path:
    """Canonical cache dir for playground run artifacts (gitignored).

    Delegates to the shared :mod:`run_store` so chatbot, survey, and web runs all
    persist to (and are listed from) the same directory.
    """
    return run_store.default_runs_dir()


def _normalize_prompts(value: Any) -> Optional[Dict[str, str]]:
    if not isinstance(value, dict):
        return None
    prompts: Dict[str, str] = {}
    for key in ("personaPrompt", "harborPrompt", "taskPrompt"):
        if key in value and value[key] is not None:
            prompts[key] = str(value[key])
    return prompts or None


@dataclass
class PlaygroundProgress:
    job_id: str
    domain: str
    persona_id: str
    persona_name: str
    sut_description: str
    application_id: str = "meal_planning_nutrition"
    application_context: Optional[str] = None
    goal_context_id: str = "scenario_default"
    status: str = "building"  # building | running | done | error
    phase: Optional[str] = None
    turns: List[Dict[str, Any]] = field(default_factory=list)
    questionnaire: Optional[Dict[str, Any]] = None
    metric_scores: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, str]] = None
    error: Optional[str] = None

    def to_view(self) -> Dict[str, Any]:
        return {
            "jobId": self.job_id,
            "domain": self.domain,
            "applicationId": self.application_id,
            "applicationContext": self.application_context,
            "personaId": self.persona_id,
            "personaName": self.persona_name,
            "sutDescription": self.sut_description,
            "goalContextId": self.goal_context_id,
            "status": self.status,
            "phase": self.phase,
            "turns": list(self.turns),
            "questionnaire": self.questionnaire,
            "metricScores": self.metric_scores,
            "prompts": self.prompts,
            "error": self.error,
        }


class PlaygroundService:
    def __init__(
        self,
        *,
        session_builder: Callable[[PlaygroundConfig], Any],
        get_persona: Callable[[str], Any],
        sut_for: Callable[[str], str],
        simulator_factory: Callable[[str, str, str], Any],
        runner: Callable[..., Any] = _default_runner,
        engine: str = "gpt-4o-mini",
        runs_dir: Optional[Path] = None,
    ) -> None:
        self._session_builder = session_builder
        self._get_persona = get_persona
        self._sut_for = sut_for
        self._simulator_factory = simulator_factory
        self._runner = runner
        self._engine = engine
        self._runs_dir = Path(runs_dir) if runs_dir is not None else _default_runs_dir()
        self._guard = threading.Lock()
        self._progress: Dict[str, PlaygroundProgress] = {}

    def start(
        self,
        domain: str,
        persona_id: str,
        max_turns: int,
        goal_context_id: str = "scenario_default",
        *,
        now: Callable[[], str],
        engine: Optional[str] = None,
        persona_model: Optional[str] = None,
        application_id: str = "meal_planning_nutrition",
        application_context: Optional[str] = None,
    ) -> str:
        # Persona is domain-free: any persona may run against any domain.
        # ``engine`` drives the recommender side of the run; ``persona_model``
        # drives the simulated user. ``None`` keeps defaults so existing
        # callers are unchanged.
        persona = self._get_persona(persona_id)
        run_engine = engine or self._engine
        run_persona_model = persona_model or DEFAULT_PERSONA_MODEL
        resolved_application_context = application_context or domain
        sut_key = resolved_application_context or domain
        job_id = _new_playground_id()
        progress = PlaygroundProgress(
            job_id=job_id,
            domain=domain,
            application_id=application_id,
            application_context=resolved_application_context,
            persona_id=persona_id,
            persona_name=getattr(persona, "name", persona_id),
            sut_description=self._sut_for(sut_key),
            goal_context_id=goal_context_id,
        )
        with self._guard:
            self._progress[job_id] = progress
        thread = threading.Thread(
            target=self._run,
            args=(progress, persona, max_turns, run_engine, run_persona_model, now),
            daemon=True,
        )
        thread.start()
        return job_id

    def view(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._guard:
            progress = self._progress.get(job_id)
            return progress.to_view() if progress else None

    # ------------------------------------------------------------------ #
    # Persisted runs (durable artifacts under ``runs_dir``)
    # ------------------------------------------------------------------ #
    def _persist_run(self, job_id: str, result: Any) -> None:
        """Write ``result.to_dict()`` (plus a top-level ``id``) atomically.

        Best-effort: a write failure must not fail the run itself, so a finished
        run still reports ``done`` even if its artifact could not be saved.
        """
        try:
            payload = result.to_dict()
        except Exception:  # noqa: BLE001 - non-serializable runner result
            return
        payload["id"] = job_id
        try:
            self._runs_dir.mkdir(parents=True, exist_ok=True)
            target = self._runs_dir / "{}.json".format(job_id)
            fd, tmp = tempfile.mkstemp(dir=str(self._runs_dir), suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    json.dump(payload, fh, ensure_ascii=False, indent=2)
                os.replace(tmp, str(target))
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
        except Exception:  # noqa: BLE001 - persistence is best-effort
            return

    def _load_run(self, path: Path) -> Optional[Dict[str, Any]]:
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else None
        except Exception:  # noqa: BLE001 - skip unreadable/corrupt artifacts
            return None

    def list_runs(self) -> List[Dict[str, Any]]:
        """Newest-first run summaries read from disk (chatbot, survey, and web).

        Each summary carries an ``applicationType`` plus the chatbot fields
        (``domain``/``goalContextId``/``numTurns`` — ``None`` for survey/web) and
        a per-type ``overallRating``; corrupt/unreadable artifacts are skipped.
        """
        summaries = [
            run_store.summarize_record(record)
            for record in run_store.iter_run_records(self._runs_dir)
        ]
        summaries.sort(key=lambda s: s.get("createdAt") or "", reverse=True)
        return summaries

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """The full stored result for ``run_id``, or ``None`` if absent.

        Guarantees a top-level ``id`` even for legacy artifacts (e.g. CLI-written
        runs keyed by persona id) that predate ``_persist_run``'s id injection, so
        the ``PlaygroundResultView`` response contract always holds.
        """
        path = self._runs_dir / "{}.json".format(run_id)
        if not path.is_file():
            return None
        data = self._load_run(path)
        if data is not None:
            data["id"] = data.get("id") or run_id
        return data

    def _run(
        self,
        progress: PlaygroundProgress,
        persona: Any,
        max_turns: int,
        engine: str,
        persona_model: str,
        now: Callable[[], str],
    ) -> None:
        with _RUN_LOCK:  # serialize all RecAI-driving playgrounds
            try:
                config = PlaygroundConfig(
                    domain=progress.domain,
                    application_id=progress.application_id,
                    application_context=progress.application_context or progress.domain,
                    engine=engine,
                    persona_model=persona_model,
                    ranker_mode="native",
                    resource_mode="recai_resources",
                    max_turns=max_turns,
                    goal_context_id=progress.goal_context_id,
                )
                session = self._session_builder(config)
                with self._guard:
                    progress.status = "running"

                def on_event(event: Dict[str, Any]) -> None:
                    etype = event.get("type")
                    if etype == "phase":
                        phase = event.get("phase")
                        with self._guard:
                            progress.phase = phase
                    elif etype == "turn":
                        with self._guard:
                            progress.turns = list(
                                getattr(session, "turns", progress.turns)
                            )
                    elif etype == "prompts":
                        prompts = _normalize_prompts(event.get("prompts"))
                        with self._guard:
                            progress.prompts = prompts
                    elif etype == "done":
                        result = event.get("result") or {}
                        questionnaire = result.get("questionnaire")
                        metric_scores = result.get("metricScores")
                        prompts = _normalize_prompts(result.get("prompts"))
                        with self._guard:
                            progress.questionnaire = questionnaire
                            progress.metric_scores = metric_scores
                            if prompts is not None:
                                progress.prompts = prompts

                simulator = self._build_simulator(
                    engine,
                    progress.goal_context_id,
                    progress.domain,
                    persona_model,
                )
                result = self._runner(
                    session,
                    persona,
                    progress.sut_description,
                    config,
                    simulator,
                    created_at=now(),
                    on_event=on_event,
                )
                self._persist_run(progress.job_id, result)
                try:
                    result_payload = result.to_dict()
                except Exception:  # noqa: BLE001 - progress can finish without rich result metadata
                    result_payload = {}
                with self._guard:
                    progress.turns = list(getattr(session, "turns", progress.turns))
                    if "questionnaire" in result_payload:
                        progress.questionnaire = result_payload.get("questionnaire")
                    if "metricScores" in result_payload:
                        progress.metric_scores = result_payload.get("metricScores")
                    prompts = _normalize_prompts(result_payload.get("prompts"))
                    if prompts is not None:
                        progress.prompts = prompts
                    progress.phase = None
                    progress.status = "done"
            except BaseException as exc:  # noqa: BLE001 - surface any failure to the client
                with self._guard:
                    progress.error = "{}: {}".format(type(exc).__name__, exc)
                    progress.status = "error"

    def _build_simulator(
        self,
        engine: str,
        goal_context_id: str,
        domain: str,
        persona_model: str,
    ) -> Any:
        """Build a simulator, supporting legacy 3-argument factories."""
        try:
            params = inspect.signature(self._simulator_factory).parameters
        except (TypeError, ValueError):
            params = {}
        if len(params) >= 4:
            return self._simulator_factory(
                engine,
                goal_context_id,
                domain,
                persona_model,
            )
        return self._simulator_factory(engine, goal_context_id, domain)
