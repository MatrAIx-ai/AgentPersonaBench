"""Async service for local Playground survey runs."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from backend.service import run_store
from backend.service.config import persona_model as default_persona_model
from backend.service.survey_types import (
    SurveyEvalConfig,
    SurveyEvalResult,
    SurveyInstrument,
)

_SURVEY_RUN_LOCK = threading.Lock()


def _new_survey_eval_id() -> str:
    return "survey_" + uuid.uuid4().hex[:12]


def _completion_for(result: SurveyEvalResult) -> Dict[str, Any]:
    answered_ids = {answer.question_id for answer in result.answers}
    missing = [
        question.id
        for question in result.instrument.questions
        if question.required and question.id not in answered_ids
    ]
    metrics = result.metrics.to_dict()
    return {
        "numQuestions": metrics["numQuestions"],
        "numAnswered": metrics["numAnswered"],
        "missingQuestionIds": missing,
        "valid": not missing,
        "meanLikert": metrics["meanLikert"],
    }


def survey_result_view(result: SurveyEvalResult) -> Dict[str, Any]:
    """Return the UI/API survey artifact view.

    The survey artifact is the evaluation result. This view deliberately avoids
    chatbot-only fields such as ``questionnaire`` or ``metricScores``.
    """
    return {
        "instrument": result.instrument.to_dict(),
        "answers": [answer.to_dict() for answer in result.answers],
        "trajectory": [event.to_dict() for event in result.trajectory],
        "completion": _completion_for(result),
        "createdAt": result.created_at,
        "prompts": dict(result.prompts),
    }


@dataclass
class SurveyEvalProgress:
    job_id: str
    instrument: SurveyInstrument
    persona_id: str
    persona_name: str
    status: str = "building"
    phase: Optional[str] = None
    survey_result: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, str]] = None
    error: Optional[str] = None

    def to_view(self) -> Dict[str, Any]:
        return {
            "jobId": self.job_id,
            "applicationType": "survey",
            "taskId": "survey_form",
            "instrumentId": self.instrument.id,
            "instrumentTitle": self.instrument.title,
            "personaId": self.persona_id,
            "personaName": self.persona_name,
            "status": self.status,
            "phase": self.phase,
            "surveyResult": self.survey_result,
            "prompts": self.prompts,
            "error": self.error,
        }


class SurveyEvalService:
    """Start and poll local survey runs for the Playground UI."""

    def __init__(
        self,
        *,
        get_persona: Callable[[str], Any],
        get_instrument: Callable[[str], SurveyInstrument],
        list_instruments: Callable[[], List[SurveyInstrument]],
        runner: Callable[..., SurveyEvalResult],
        runs_dir: Optional[Path] = None,
    ) -> None:
        self._get_persona = get_persona
        self._get_instrument = get_instrument
        self._list_instruments = list_instruments
        self._runner = runner
        self._runs_dir = runs_dir or run_store.default_runs_dir()
        self._guard = threading.Lock()
        self._progress: Dict[str, SurveyEvalProgress] = {}

    def list_instruments(self) -> List[Dict[str, Any]]:
        return [instrument.to_dict() for instrument in self._list_instruments()]

    def start(
        self,
        *,
        persona_id: str,
        instrument_id: str,
        persona_model: Optional[str],
        now: Callable[[], str],
    ) -> str:
        persona = self._get_persona(persona_id)
        instrument = self._get_instrument(instrument_id)
        job_id = _new_survey_eval_id()
        progress = SurveyEvalProgress(
            job_id=job_id,
            instrument=instrument,
            persona_id=persona_id,
            persona_name=getattr(persona, "name", persona_id),
        )
        with self._guard:
            self._progress[job_id] = progress
        thread = threading.Thread(
            target=self._run,
            args=(progress, persona, instrument, persona_model, now),
            daemon=True,
        )
        thread.start()
        return job_id

    def view(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._guard:
            progress = self._progress.get(job_id)
            return progress.to_view() if progress else None

    def _run(
        self,
        progress: SurveyEvalProgress,
        persona: Any,
        instrument: SurveyInstrument,
        persona_model: Optional[str],
        now: Callable[[], str],
    ) -> None:
        with _SURVEY_RUN_LOCK:
            try:
                config = SurveyEvalConfig(
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
                                progress.survey_result = {
                                    "instrument": result.get("instrument"),
                                    "answers": result.get("answers"),
                                    "trajectory": result.get("trajectory"),
                                    "completion": {
                                        "numQuestions": (
                                            result.get("metrics") or {}
                                        ).get("numQuestions"),
                                        "numAnswered": (
                                            result.get("metrics") or {}
                                        ).get("numAnswered"),
                                        "missingQuestionIds": [],
                                        "valid": True,
                                        "meanLikert": (
                                            result.get("metrics") or {}
                                        ).get("meanLikert"),
                                    },
                                    "createdAt": result.get("createdAt"),
                                    "prompts": result.get("prompts"),
                                }

                result = self._runner(
                    persona,
                    instrument,
                    config,
                    created_at=now(),
                    on_event=on_event,
                )
                result_view = survey_result_view(result)
                # Persist as a run BEFORE marking done so a "done" run is always
                # already saved (it shows in Runs and survives a restart).
                # Best-effort: never fails the run.
                run_store.persist_run(
                    self._runs_dir,
                    {
                        "id": progress.job_id,
                        "applicationType": "survey",
                        "createdAt": result_view.get("createdAt"),
                        "persona": run_store.persona_summary(persona),
                        "instrumentTitle": instrument.title,
                        "surveyResult": result_view,
                    },
                )
                with self._guard:
                    progress.survey_result = result_view
                    progress.prompts = result_view.get("prompts")
                    progress.phase = None
                    progress.status = "done"
            except BaseException as exc:  # noqa: BLE001 - surface to client
                with self._guard:
                    progress.error = "{}: {}".format(type(exc).__name__, exc)
                    progress.status = "error"
