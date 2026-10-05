"""Async-job registry for running blocking recommendation turns off the loop.

``recbot.interecagent_bridge.run_turn`` is **blocking** and the first call is a
multi-minute cold start (the RecAI agent is built and cached in-process). The
FastAPI app therefore never runs a turn inside a request handler. Instead:

1. ``POST /api/sessions/{id}/turns`` calls :meth:`JobRegistry.submit`, which
   registers a job, hands the work to a :class:`~concurrent.futures.ThreadPoolExecutor`,
   and returns a ``job_id`` immediately.
2. The browser polls ``GET /api/jobs/{job_id}``; the API reads
   :meth:`JobRegistry.get`, which reports the job's lifecycle:

       building -> running -> done | error

   ``building`` covers the time the worker is queued / waiting for the
   per-session lock / cold-starting the agent; ``running`` is flipped on right
   before the actual turn executes; ``done`` carries the ``TurnView`` and
   ``error`` carries a message.

Turns are **serialized per session** via ``_session_locks``, a dict of
:class:`threading.Lock` objects keyed by session ID.  This prevents two turns
for the *same* session from overlapping, but it does **not** protect against
cross-session interference.  When the RecAI bridge runs in-process it uses a
module-global cached agent and mutates ``os.environ`` (e.g.
``MATRAIX_CURRENT_USER_REQUEST``) and shared candidate-buffer state; concurrent
turns for *different* sessions running in the same process can therefore clobber
each other's environment and candidate buffer.  Turns are therefore serialized
per session (and the in-process bridge is the only execution mode).

This module is stdlib-only and imports nothing from ``recbot`` — the heavy work
is supplied as a plain callable by the caller (the session manager), so the
registry stays importable and unit-testable without RecAI / numpy / pandas.
"""

from __future__ import annotations

import datetime as _dt
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, Optional

__all__ = ["JobStatus", "Job", "JobRegistry"]


# Lifecycle states, mirroring the frontend ``JobStatus`` union.
JobStatus = str  # one of: "building", "running", "done", "error"

_BUILDING = "building"
_RUNNING = "running"
_DONE = "done"
_ERROR = "error"

#: Terminal states a job can rest in.
TERMINAL_STATES = frozenset({_DONE, _ERROR})


def _now_iso() -> str:
    """UTC timestamp in ISO-8601 with a trailing ``Z``."""
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_job_id() -> str:
    return "job_{}".format(uuid.uuid4().hex[:12])


#: Signature of the work a job runs: ``(session_id, message) -> TurnView dict``.
TurnRunner = Callable[[str, str], Dict[str, Any]]

#: Optional callback the runner may call to flip ``building`` -> ``running``.
StartedHook = Callable[[], None]


class Job:
    """Mutable record of one async turn, guarded by :class:`JobRegistry`.

    Instances are created in the ``building`` state and mutated by the worker
    thread as the turn progresses. All field access from outside the worker goes
    through :class:`JobRegistry`, which holds a lock while snapshotting.
    """

    __slots__ = (
        "id",
        "session_id",
        "message",
        "status",
        "result",
        "error",
        "created_at",
        "started_at",
        "finished_at",
        "_start_monotonic",
        "duration_seconds",
    )

    def __init__(self, job_id: str, session_id: str, message: str):
        self.id: str = job_id
        self.session_id: str = session_id
        self.message: str = message
        self.status: JobStatus = _BUILDING
        #: Populated on success: the ``TurnView`` dict from the session.
        self.result: Optional[Dict[str, Any]] = None
        #: Populated on failure: a human-readable error message.
        self.error: Optional[str] = None
        self.created_at: str = _now_iso()
        self.started_at: Optional[str] = None
        self.finished_at: Optional[str] = None
        self._start_monotonic: Optional[float] = None
        #: Wall-clock seconds the turn actually ran (set on terminal state).
        self.duration_seconds: Optional[float] = None

    # ------------------------------------------------------------------ #
    # State transitions (only ever called by the worker thread, under the
    # registry lock for the status write).
    # ------------------------------------------------------------------ #
    def mark_running(self) -> None:
        self.status = _RUNNING
        self.started_at = _now_iso()
        self._start_monotonic = time.monotonic()

    def mark_done(self, result: Dict[str, Any]) -> None:
        self.result = result
        self.status = _DONE
        self._finish()

    def mark_error(self, message: str) -> None:
        self.error = message
        self.status = _ERROR
        self._finish()

    def _finish(self) -> None:
        self.finished_at = _now_iso()
        if self._start_monotonic is not None:
            self.duration_seconds = round(time.monotonic() - self._start_monotonic, 3)

    # ------------------------------------------------------------------ #
    # Views
    # ------------------------------------------------------------------ #
    def to_view(self) -> Dict[str, Any]:
        """Return the ``GET /api/jobs/{id}`` payload (camelCase wire shape).

        Shape matches the frontend ``JobView``::

            {"jobId", "status", "turn"?, "error"?, ...timing}

        ``turn`` is the resolved ``TurnView`` (only on ``done``); ``error`` is
        the message (only on ``error``). The duplicate ``result`` key is
        included as a convenience alias for the API-contract naming
        (``result?: TurnView``); both point at the same object.
        """
        view: Dict[str, Any] = {
            "jobId": self.id,
            "sessionId": self.session_id,
            "status": self.status,
            "turn": self.result if self.status == _DONE else None,
            "result": self.result if self.status == _DONE else None,
            "error": self.error if self.status == _ERROR else None,
            "createdAt": self.created_at,
            "startedAt": self.started_at,
            "finishedAt": self.finished_at,
            "durationSeconds": self.duration_seconds,
        }
        return view


class JobRegistry:
    """Submit turns to a thread pool and track their lifecycle.

    Parameters
    ----------
    runner:
        The blocking work to run for a job: ``runner(session_id, message)``
        returning a ``TurnView`` dict. Typically
        :meth:`backend.service.session.SessionManager.run_turn_sync`.
    max_workers:
        Thread-pool size. Turns for the *same* session are serialized by a
        per-session lock regardless of this value; this bounds concurrency
        across *different* sessions. Defaults to 4.
    max_jobs:
        Soft cap on retained finished jobs. When exceeded, the oldest terminal
        jobs are evicted so the registry does not grow without bound during a
        long-lived single-worker process.
    """

    def __init__(
        self,
        runner: TurnRunner,
        max_workers: int = 4,
        max_jobs: int = 512,
    ):
        self._runner = runner
        self._executor = ThreadPoolExecutor(
            max_workers=max(1, int(max_workers)),
            thread_name_prefix="recbot-turn",
        )
        self._max_jobs = max(16, int(max_jobs))
        self._jobs: Dict[str, Job] = {}
        #: Insertion order of job ids, used for eviction of old terminal jobs.
        self._order: list = []
        #: One lock per session id -> serialize that session's turns.
        self._session_locks: Dict[str, threading.Lock] = {}
        #: Guards _jobs / _order / _session_locks mutation.
        self._guard = threading.Lock()

    # ------------------------------------------------------------------ #
    # Submission
    # ------------------------------------------------------------------ #
    def submit(self, session_id: str, message: str) -> str:
        """Register and dispatch a turn; return its ``job_id`` immediately.

        The job starts in ``building``. A pool thread then acquires the
        session's lock (still ``building`` — this models queueing behind another
        in-flight turn and/or the agent cold start), flips to ``running`` just
        before executing, and finally records ``done`` / ``error``.
        """
        job_id = _new_job_id()
        job = Job(job_id, session_id, message)
        with self._guard:
            self._jobs[job_id] = job
            self._order.append(job_id)
            self._evict_locked()
        self._executor.submit(self._run_job, job)
        return job_id

    # ------------------------------------------------------------------ #
    # Worker body
    # ------------------------------------------------------------------ #
    def _run_job(self, job: Job) -> None:
        """Execute a single job on a pool thread (serialized per session)."""
        lock = self._lock_for(job.session_id)
        # Hold the per-session lock for the whole turn: the agent is a global
        # singleton and must not run two turns for one session at once.
        with lock:
            try:
                with self._guard:
                    job.mark_running()
                result = self._runner(job.session_id, job.message)
                with self._guard:
                    job.mark_done(result if isinstance(result, dict) else {"result": result})
            except BaseException as exc:  # noqa: BLE001 - surface any failure
                with self._guard:
                    job.mark_error(_describe_exception(exc))

    # ------------------------------------------------------------------ #
    # Lookup
    # ------------------------------------------------------------------ #
    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Return the job view dict for ``job_id``, or ``None`` if unknown."""
        with self._guard:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return job.to_view()

    def get_job(self, job_id: str) -> Optional[Job]:
        """Return the raw :class:`Job` (mostly for tests)."""
        with self._guard:
            return self._jobs.get(job_id)

    def is_terminal(self, job_id: str) -> bool:
        """``True`` if ``job_id`` exists and has reached a terminal state."""
        with self._guard:
            job = self._jobs.get(job_id)
            return bool(job and job.status in TERMINAL_STATES)

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def shutdown(self, wait: bool = False) -> None:
        """Shut the executor down (used on app shutdown / in tests)."""
        self._executor.shutdown(wait=wait)

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _lock_for(self, session_id: str) -> threading.Lock:
        with self._guard:
            lock = self._session_locks.get(session_id)
            if lock is None:
                lock = threading.Lock()
                self._session_locks[session_id] = lock
            return lock

    def _evict_locked(self) -> None:
        """Drop oldest terminal jobs when over the retention cap.

        Caller must hold ``self._guard``. Never evicts non-terminal (in-flight)
        jobs, so an active poll target is always present.
        """
        if len(self._jobs) <= self._max_jobs:
            return
        overflow = len(self._jobs) - self._max_jobs
        survivors: list = []
        removed = 0
        for jid in self._order:
            job = self._jobs.get(jid)
            if job is None:
                continue
            if removed < overflow and job.status in TERMINAL_STATES:
                self._jobs.pop(jid, None)
                removed += 1
            else:
                survivors.append(jid)
        self._order = survivors


def _describe_exception(exc: BaseException) -> str:
    """Compact, user-facing description of a turn failure."""
    name = type(exc).__name__
    text = str(exc).strip()
    if text:
        return "{}: {}".format(name, text)
    return name
