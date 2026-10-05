"""Conversation sessions and the manager that owns them.

A :class:`RecBotSession` holds the state of one chat with the recommendation
bot: its id, title, the active Studio :class:`ConfigManager` config, the running
list of messages, and a list of per-turn ``TurnView`` dicts.

Running a turn (:meth:`RecBotSession.run_turn_sync`) is where the harness
touches the real backend. It is **blocking** and the first call is a multi-minute
cold start, so the API runs it in a threadpool under a per-session lock. To keep
this module importable without RecAI / numpy / pandas installed, the heavyweight
:func:`recbot.interecagent_bridge.run_turn` is imported **lazily inside**
:meth:`run_turn_sync`.

:class:`SessionManager` is the in-memory registry of sessions used by the API.
It owns a :class:`~backend.service.session_store.SessionStore` for persistence,
a shared :class:`~backend.service.catalog_index.CatalogIndex`, a
:class:`~backend.service.config.ConfigManager`. Per-session turn serialization
is handled by :class:`~backend.service.jobs.JobRegistry` via threading.Lock.
"""

from __future__ import annotations

import datetime as _dt
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from backend.service.catalog_index import CatalogIndex
from backend.service.config import ConfigManager
from backend.service.session_store import SessionStore
from backend.service.trace_view import TraceView, normalize_turn_view

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids spawning threads
    from backend.service.jobs import JobRegistry

__all__ = ["ChatTurn", "RecBotSession", "SessionManager"]

_AGENT_ERROR_PREFIX = "Something went wrong, please retry."
_TURN_ATTEMPTS = 2
# Chat applications that route to HTTP sidecars instead of the removed
# in-process RecAI engine.
_SIDECAR_APPLICATION_IDS = (
    "finance_openbb",
    "meal_planning_nutrition",
    "acme_support_api",
)
_SIDECAR_APPLICATION_CONTEXT = {
    "finance_openbb": "financial_research",
    "meal_planning_nutrition": "meal_planning",
    "acme_support_api": "customer_support",
}
_TRUNCATION_TAIL_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "because",
    "but",
    "by",
    "for",
    "from",
    "in",
    "into",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "with",
}


def _now_iso() -> str:
    """UTC timestamp in ISO-8601 with a trailing ``Z``."""
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_id(prefix: str) -> str:
    return "{}_{}".format(prefix, uuid.uuid4().hex[:12])


def _assistant_needs_retry(value: Any) -> bool:
    """Return true for RecAI turns that should not enter chat history yet."""
    if not isinstance(value, str):
        return True
    text = value.strip()
    if not text or text.startswith(_AGENT_ERROR_PREFIX):
        return True
    return _looks_truncated(text)


def _looks_truncated(text: str) -> bool:
    """Heuristic for occasional RecAI/OpenAI responses cut off mid-sentence."""
    stripped = text.strip()
    if len(stripped) < 80:
        return False
    if stripped[-1] in ".?!)]}\"'":
        return False
    if stripped[-1] in ",;:":
        return True
    words = stripped.lower().split()
    return bool(words and words[-1].strip(".,;:!?)]}\"'") in _TRUNCATION_TAIL_WORDS)


@dataclass
class ChatTurn:
    """One user/assistant exchange plus its parsed ``TurnView``.

    A lightweight, JSON-serializable record of a single conversational turn. The
    ``view`` is the camelCase ``TurnView`` dict produced by
    :meth:`backend.service.trace_view.TraceView.from_result` and is what the UI
    renders; the bare ``user_message`` / ``assistant_message`` are kept for
    convenience and so a turn round-trips even if the view changes shape.
    """

    user_message: str
    assistant_message: Optional[str] = None
    view: Dict[str, Any] = field(default_factory=dict)
    turn_id: Optional[str] = None
    created_at: str = field(default_factory=_now_iso)
    duration_seconds: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Return the JSON-serializable form (the ``TurnView`` dict).

        The persisted/rail-facing representation of a turn IS its ``view`` dict
        (so ``Session.turns`` stays a flat list of ``TurnView``s, matching the
        wire contract). ``ChatTurn`` is the in-memory convenience wrapper.
        """
        return dict(self.view)

    @classmethod
    def from_view(cls, view: Dict[str, Any]) -> "ChatTurn":
        """Rehydrate a :class:`ChatTurn` from a persisted ``TurnView`` dict."""
        view = view or {}
        return cls(
            user_message=str(view.get("userMessage") or ""),
            assistant_message=view.get("assistantMessage"),
            view=dict(view),
            turn_id=view.get("turnId"),
            duration_seconds=view.get("durationSeconds"),
        )


class RecBotSession:
    """A single conversation with the recommendation bot.

    Attributes
    ----------
    id, title, config, messages, turns, createdAt:
        See the API ``Session`` contract. ``messages`` is a list of
        ``{"role", "content"}`` dicts; ``turns`` is a list of ``TurnView`` dicts
        produced by :class:`~backend.service.trace_view.TraceView`.
    """

    def __init__(
        self,
        id: str,
        title: str,
        config: Dict[str, Any],
        catalog: Optional[CatalogIndex] = None,
        config_manager: Optional[ConfigManager] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        turns: Optional[List[Dict[str, Any]]] = None,
        createdAt: Optional[str] = None,
    ):
        self.id = id
        self.title = title
        self.config: Dict[str, Any] = dict(config)
        self.messages: List[Dict[str, Any]] = list(messages or [])
        self.turns: List[Dict[str, Any]] = list(turns or [])
        self.createdAt: str = createdAt or _now_iso()
        self._catalog = catalog if catalog is not None else CatalogIndex(None)
        self._config_manager = config_manager or ConfigManager()
        # Lazily created HTTP-sidecar session for finance/medical chats; RecAI
        # chats never touch it. Held per session so the sidecar conversation id
        # carries across turns within this process.
        self._direct_session: Any = None

    # ------------------------------------------------------------------ #
    # Serialization
    # ------------------------------------------------------------------ #
    def to_dict(self) -> Dict[str, Any]:
        """Return the JSON-serializable ``Session`` view."""
        return {
            "id": self.id,
            "title": self.title,
            "config": dict(self.config),
            "messages": [dict(m) for m in self.messages],
            "turns": [dict(t) for t in self.turns],
            "createdAt": self.createdAt,
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        catalog: Optional[CatalogIndex] = None,
        config_manager: Optional[ConfigManager] = None,
    ) -> "RecBotSession":
        """Rehydrate a session from its persisted dict.

        Persisted turns are passed through :func:`normalize_turn_view` so legacy
        artifacts (``turnId`` stored as an int, missing ``plan`` /
        ``structuredExposure``) are coerced to the wire contract on read — the
        session re-serializes clean and ``GET /api/sessions/{id}`` no longer
        500s on response validation.
        """
        raw_turns = data.get("turns") or []
        turns = [
            normalize_turn_view(t) for t in raw_turns if isinstance(t, dict)
        ]
        return cls(
            id=str(data.get("id")),
            title=str(data.get("title") or "Untitled session"),
            config=data.get("config") or {},
            catalog=catalog,
            config_manager=config_manager,
            messages=data.get("messages") or [],
            turns=turns,
            createdAt=data.get("createdAt"),
        )

    def summary(self) -> Dict[str, Any]:
        """Lightweight summary for the session rail."""
        return {
            "id": self.id,
            "title": self.title,
            "config": dict(self.config),
            "turnCount": len(self.turns),
            "messageCount": len(self.messages),
            "createdAt": self.createdAt,
        }

    # ------------------------------------------------------------------ #
    # Request building / turn execution
    # ------------------------------------------------------------------ #
    def build_request(self, user_message: str):
        """Build a :class:`recbot.types.RecBotRequest` for ``user_message``.

        The request carries the full message history (existing messages plus the
        new user turn) so the backend has conversational context. Imports
        ``recbot.types`` lazily so this stays importable without RecAI.

        ``RecBotRequest`` is constructed defensively: we try the full keyword
        form and progressively fall back if the installed dataclass does not
        accept ``metadata`` / ``turn_id``, so the harness tolerates minor
        backend signature drift without crashing a turn.
        """
        from recbot.types import RecBotRequest  # lazy: avoids RecAI at import

        messages: List[Dict[str, Any]] = [dict(m) for m in self.messages]
        messages.append({"role": "user", "content": user_message})
        # ``recbot.types.RecBotRequest`` validates ``turn_id`` as a non-negative
        # int, so use this turn's 0-based index rather than a string id.
        turn_id = len(self.turns)
        metadata = {
            "title": self.title,
            "config": dict(self.config),
            "studio": True,
        }
        attempts = (
            dict(
                conversation_id=self.id,
                turn_id=turn_id,
                messages=messages,
                metadata=metadata,
            ),
            dict(conversation_id=self.id, turn_id=turn_id, messages=messages),
            dict(conversation_id=self.id, messages=messages),
            dict(messages=messages),
        )
        last_error: Optional[TypeError] = None
        for kwargs in attempts:
            try:
                return RecBotRequest(**kwargs)
            except TypeError as exc:
                last_error = exc
        # Re-raise the most permissive attempt's error for a clear message.
        raise last_error if last_error is not None else TypeError(
            "could not construct RecBotRequest"
        )

    def add_user_message(self, content: str) -> Dict[str, Any]:
        """Append a user message to the running history and return it.

        Kept distinct from :meth:`run_turn` so callers can stage the user turn
        (e.g. for optimistic UI) before the blocking backend call. ``run_turn``
        does NOT call this — it manages history itself once a result is in — so
        do not use both for the same message.
        """
        msg = {"role": "user", "content": content}
        self.messages.append(msg)
        return dict(msg)

    def run_turn(self, user_message: str) -> Dict[str, Any]:
        """Contract alias for :meth:`run_turn_sync` (run one blocking turn)."""
        return self.run_turn_sync(user_message)

    def run_turn_sync(self, user_message: str) -> Dict[str, Any]:
        """Run one blocking turn through the backend; return a ``TurnView`` dict.

        Steps:

        1. Apply the session config to the environment via
           :meth:`ConfigManager.apply`, and default
           ``INTERECAGENT_CATALOG_PATH`` if unset.
        2. Lazily import :func:`recbot.interecagent_bridge.run_turn`.
        3. Build a :class:`recbot.types.RecBotRequest` and run the turn (timed).
        4. Convert the result to a ``TurnView`` with
           :meth:`TraceView.from_result`.
        5. Append the user + assistant messages and the turn to this session.

        This call is blocking and may take minutes on the first turn (agent cold
        start). The caller is responsible for running it off the event loop and
        for serializing turns per session.
        """
        # 0) Route kept chat applications to their HTTP sidecar.
        application_id = str(
            self.config.get("applicationId") or "meal_planning_nutrition"
        )
        if application_id in _SIDECAR_APPLICATION_IDS:
            return self._run_sidecar_turn(application_id, user_message)

        # 1) Environment: backend config + catalog path.
        self._config_manager.apply(self.config)
        catalog_path = os.environ.get("INTERECAGENT_CATALOG_PATH")
        if not catalog_path:
            default_path = self._catalog_path_default()
            if default_path:
                os.environ["INTERECAGENT_CATALOG_PATH"] = default_path

        # 2) Build the request, then run it through the real backend. We lazily
        #    import the heavyweight bridge (which pulls numpy/pandas/RecAI) and
        #    run the turn in-process so this module stays importable without
        #    RecAI installed.
        request = self.build_request(user_message)
        from recbot.interecagent_bridge import run_turn  # lazy import

        turn_view: Dict[str, Any] = {}
        total_duration_seconds = 0.0
        for attempt in range(_TURN_ATTEMPTS):
            started = time.monotonic()
            result = run_turn(request)
            total_duration_seconds += time.monotonic() - started

            # 4) Build the UI view (TraceView normalizes result -> dict itself).
            turn_view = TraceView.from_result(
                result,
                self._catalog,
                duration_seconds=round(total_duration_seconds, 3),
            )
            if (
                attempt >= _TURN_ATTEMPTS - 1
                or not _assistant_needs_retry(turn_view.get("assistantMessage"))
            ):
                break

        # 5) Update conversation state.
        assistant_text = turn_view.get("assistantMessage")
        self.messages.append({"role": "user", "content": user_message})
        if isinstance(assistant_text, str):
            self.messages.append({"role": "assistant", "content": assistant_text})
        self.turns.append(turn_view)
        return turn_view

    def _run_sidecar_turn(self, application_id: str, user_message: str) -> Dict[str, Any]:
        """Run one turn against a finance/medical HTTP chatbot sidecar.

        Routes to the same adapter the Playground uses. A sidecar that
        is offline raises a clear 503 (surfaced as the turn error) rather than
        silently falling back to RecAI. The sidecar response is adapted into the
        same ``TurnView`` shape the chat UI and persistence expect.
        """
        from playground.inprocess.chatbot_eval import DirectApplicationSession
        from playground.types import PlaygroundConfig

        if self._direct_session is None:
            self._direct_session = DirectApplicationSession(
                PlaygroundConfig(
                    application_id=application_id,
                    application_context=_SIDECAR_APPLICATION_CONTEXT.get(application_id, ""),
                    engine=str(self.config.get("engine") or "gpt-4o-mini"),
                )
            )

        started = time.monotonic()
        turn = self._direct_session.run_turn_sync(user_message)
        duration_seconds = round(time.monotonic() - started, 3)

        turn_view = normalize_turn_view(
            {
                "turnId": turn.get("turnId") or _new_id("turn"),
                "userMessage": user_message,
                "assistantMessage": turn.get("assistantMessage") or "",
                "plan": [],
                "structuredExposure": turn.get("structuredExposure") or [],
                "durationSeconds": duration_seconds,
                "raw": turn,
            }
        )

        assistant_text = turn_view.get("assistantMessage")
        self.messages.append({"role": "user", "content": user_message})
        if isinstance(assistant_text, str) and assistant_text:
            self.messages.append({"role": "assistant", "content": assistant_text})
        self.turns.append(turn_view)
        return turn_view

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _catalog_path_default(self) -> Optional[str]:
        """Explicit JSONL catalog path to expose to the backend, if any.

        Returns the loaded index's ``catalog_path`` when it was built from a
        JSONL file (tests / a pinned catalog). The real per-domain bundle index
        has no file path, so this returns ``None`` — the bridge then resolves
        the catalog from the domain bundle, and ``INTERECAGENT_CATALOG_PATH``
        stays unset (it only feeds the agent cache key).
        """
        return getattr(self._catalog, "catalog_path", None)


class SessionManager:
    """In-memory registry of sessions with process-wide turn serialization.

    Holds the shared catalog index, config manager, and session store.

    Turns are serialized **process-wide** (``max_turn_workers`` defaults to 1):
    the in-process RecAI bridge mutates shared global state on every turn
    (``os.environ``, ``sys.path``, and a module-global agent cache keyed by
    domain/engine/botType), so running two turns concurrently — even for
    *different* sessions — would corrupt each other's domain/agent/candidate
    state. A single turn worker makes the global mutation safe; ``JobRegistry``
    additionally holds a per-session lock for same-session ordering.
    """

    def __init__(
        self,
        catalog: Optional[CatalogIndex] = None,
        store: Optional[SessionStore] = None,
        config_manager: Optional[ConfigManager] = None,
        max_turn_workers: int = 1,
    ):
        self.catalog = catalog if catalog is not None else CatalogIndex(None)
        self.store = store if store is not None else SessionStore()
        self.config = config_manager or ConfigManager()
        self._sessions: Dict[str, RecBotSession] = {}
        # Guards _sessions mutation across the threadpool.
        self._guard = threading.Lock()
        self._max_turn_workers = max(1, int(max_turn_workers))
        # Lazily-created so importing the manager never spins up threads; the
        # API creates it on first turn submission.
        self._jobs: Optional["JobRegistry"] = None

    # ------------------------------------------------------------------ #
    # CRUD
    # ------------------------------------------------------------------ #
    def create(
        self,
        title: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> RecBotSession:
        """Create, register, and persist a new session."""
        normalized = self.config.normalize(config)
        session = RecBotSession(
            id=_new_id("ses"),
            title=(title or "").strip() or "New session",
            config=normalized,
            catalog=self.catalog,
            config_manager=self.config,
        )
        with self._guard:
            self._sessions[session.id] = session
        self._persist(session)
        return session

    def get(self, session_id: str) -> Optional[RecBotSession]:
        """Return a session by id, loading it from disk if not in memory."""
        with self._guard:
            session = self._sessions.get(session_id)
        if session is not None:
            return session
        # Fall back to disk (e.g. after a restart) and cache it.
        data = self.store.load(session_id)
        if data is None:
            return None
        session = RecBotSession.from_dict(
            data, catalog=self.catalog, config_manager=self.config
        )
        with self._guard:
            # Re-check in case another thread loaded it concurrently.
            existing = self._sessions.get(session_id)
            if existing is not None:
                return existing
            self._sessions[session_id] = session
        return session

    def list(self) -> List[Dict[str, Any]]:
        """Return session summaries, merging in-memory and on-disk sessions.

        In-memory sessions take precedence (they are the freshest); any
        on-disk-only sessions are appended. Sorted newest-first by ``createdAt``.
        """
        with self._guard:
            in_memory = {sid: s.summary() for sid, s in self._sessions.items()}
        summaries: Dict[str, Dict[str, Any]] = dict(in_memory)
        for disk_summary in self.store.list():
            sid = disk_summary.get("id")
            if isinstance(sid, str) and sid not in summaries:
                summaries[sid] = disk_summary
        ordered = list(summaries.values())
        ordered.sort(
            key=lambda s: (s.get("createdAt") or "", s.get("id") or ""),
            reverse=True,
        )
        return ordered

    def delete(self, session_id: str) -> bool:
        """Remove a session from memory and disk; True if it existed anywhere."""
        with self._guard:
            in_memory = self._sessions.pop(session_id, None) is not None
        on_disk = self.store.delete(session_id)
        return in_memory or on_disk

    def clear(self) -> int:
        """Remove every session (memory + disk); return the number removed."""
        with self._guard:
            ids = set(self._sessions.keys())
            self._sessions.clear()
        for disk_summary in self.store.list():
            sid = disk_summary.get("id")
            if isinstance(sid, str):
                ids.add(sid)
        for sid in ids:
            self.store.delete(sid)
        return len(ids)

    def patch_config(
        self, session_id: str, cfg: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Merge a config patch into a session; report cache invalidation.

        Returns ``None`` if the session does not exist; otherwise
        ``{"session": <session>, "cacheInvalidated": <bool>}`` where the bool
        indicates whether the change forces an agent rebuild (cold start) on the
        next turn.
        """
        session = self.get(session_id)
        if session is None:
            return None
        old_config = dict(session.config)
        merged = dict(old_config)
        # Validate the patch keys/values, then merge.
        self.config.validate(cfg)
        merged.update(cfg)
        new_config = self.config.normalize(merged)
        invalidated = self.config.cache_invalidating(old_config, new_config)
        session.config = new_config
        self._persist(session)
        return {"session": session, "cacheInvalidated": invalidated}

    # ------------------------------------------------------------------ #
    # Concurrency / turns
    # ------------------------------------------------------------------ #
    def run_turn_sync(self, session_id: str, message: str) -> Dict[str, Any]:
        """Run a blocking turn for ``session_id`` and persist the session.

        Intended to be called inside a threadpool (the blocking work). The
        :class:`~backend.service.jobs.JobRegistry` serializes calls per session
        via its own per-session lock, so this method does not lock here. Raises
        ``KeyError`` if the session is unknown so the job layer can surface a
        clean error.
        """
        session = self.get(session_id)
        if session is None:
            raise KeyError("unknown session: {}".format(session_id))
        turn_view = session.run_turn_sync(message)
        self._persist(session)
        return turn_view

    # ------------------------------------------------------------------ #
    # Async jobs (the API's turn flow)
    # ------------------------------------------------------------------ #
    @property
    def jobs(self) -> "JobRegistry":
        """The lazily-created :class:`~backend.service.jobs.JobRegistry`.

        Wired to :meth:`run_turn_sync` so every job runs a real turn and
        persists the session. Created on first access to avoid spawning the
        thread pool at import time.
        """
        if self._jobs is None:
            from backend.service.jobs import JobRegistry

            self._jobs = JobRegistry(
                runner=self.run_turn_sync,
                max_workers=self._max_turn_workers,
            )
        return self._jobs

    def submit_turn(self, session_id: str, message: str) -> str:
        """Submit an async turn; return a ``job_id`` to poll immediately.

        Validates the session exists and the message is non-empty up front so
        the API can return a clean 404 / 400 instead of failing inside a worker.
        """
        if self.get(session_id) is None:
            raise KeyError("unknown session: {}".format(session_id))
        text = (message or "").strip()
        if not text:
            raise ValueError("message must not be empty")
        return self.jobs.submit(session_id, text)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Return the job view dict for ``job_id`` (or ``None`` if unknown)."""
        return self.jobs.get(job_id)

    def shutdown(self) -> None:
        """Release background resources (the job thread pool)."""
        if self._jobs is not None:
            self._jobs.shutdown(wait=False)

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _persist(self, session: RecBotSession) -> None:
        try:
            self.store.save(session.to_dict())
        except OSError:
            # Persistence is best-effort; an unwritable cache dir should not
            # break the live in-memory session.
            pass
