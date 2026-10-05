"""Shared pytest fixtures for the Playground backend tests.

This module does three load-bearing things so the whole suite runs with **no**
RecAI / OpenAI / numpy / pandas / network present:

1. **Fakes the ``recbot`` backend.** A real turn would drive RecAI / an LLM, so
   we replace the real backend package (``recbot.interecagent_bridge`` /
   ``recbot.types``) with a faithful in-memory fake. The service layer imports it
   *lazily* (inside
   :meth:`backend.service.session.RecBotSession.run_turn_sync` and
   ``build_request``), so the fake only has to be present while a test *runs* —
   the autouse ``_fake_recbot`` fixture installs it into ``sys.modules`` per test
   and restores the prior entries on teardown. That scoping keeps the fake from
   leaking into a sibling suite (e.g. ``recbot/tests``) that needs the real
   ``recbot`` package when both are collected in one ``pytest`` invocation. The
   fake mirrors the documented dataclass contract: ``RecBotRequest``,
   ``RecBotTurnResult``, ``NativeAction``, ``RecBotTrace``, ``ChatMessage`` (each
   with ``to_dict`` / ``from_dict``), and a
   ``run_turn(request) -> RecBotTurnResult`` in the bridge module.

2. **Isolates persistence.** :class:`~backend.service.session_store.SessionStore`
   defaults to a repo ``data/cache/...`` directory; we monkeypatch its
   ``_default_base_dir`` to a per-test ``tmp_path`` so tests never touch the
   repo and never collide.

3. **Provides ready-made objects**: a temp ``items.jsonl`` + path, a
   :class:`~backend.service.catalog_index.CatalogIndex` over it, a
   :class:`~backend.service.session.SessionManager`, and a FastAPI
   ``TestClient`` built from :func:`backend.api.app.create_app`.

The fake ``run_turn`` is monkeypatchable per-test: it reads the current
``recbot.interecagent_bridge.run_turn`` at call time (the service does
``from recbot.interecagent_bridge import run_turn`` lazily, so reassigning the
attribute before the turn runs takes effect). Tests can swap it via the
``set_run_turn`` fixture to drive specific outputs or errors.
"""

from __future__ import annotations

import json
import os
import sys
import types
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pytest


# --------------------------------------------------------------------------- #
# Fake ``recbot`` backend (installed into sys.modules at import time)
# --------------------------------------------------------------------------- #
@dataclass
class ChatMessage:
    """Minimal stand-in for ``recbot.types.ChatMessage``."""

    role: str
    content: str

    def to_dict(self) -> Dict[str, Any]:
        return {"role": self.role, "content": self.content}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessage":
        return cls(role=data.get("role", ""), content=data.get("content", ""))


@dataclass
class RecBotRequest:
    """Stand-in for ``recbot.types.RecBotRequest``.

    Accepts the full keyword form the session builds
    (``conversation_id`` / ``turn_id`` / ``messages`` / ``metadata``) so the
    first (most complete) construction attempt in
    :meth:`RecBotSession.build_request` succeeds.
    """

    messages: List[Dict[str, Any]] = field(default_factory=list)
    conversation_id: Optional[str] = None
    turn_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "turn_id": self.turn_id,
            "messages": [dict(m) for m in self.messages],
            "metadata": dict(self.metadata) if self.metadata else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RecBotRequest":
        return cls(
            messages=list(data.get("messages") or []),
            conversation_id=data.get("conversation_id"),
            turn_id=data.get("turn_id"),
            metadata=data.get("metadata"),
        )


@dataclass
class NativeAction:
    """Stand-in for ``recbot.types.NativeAction``."""

    raw: Any = None
    raw_tool_plan: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {"raw": self.raw, "raw_tool_plan": self.raw_tool_plan}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NativeAction":
        return cls(raw=data.get("raw"), raw_tool_plan=data.get("raw_tool_plan"))


@dataclass
class RecBotTrace:
    """Stand-in for ``recbot.types.RecBotTrace``."""

    raw_tool_plan: Any = None
    raw_tool_outputs: Any = None
    recommended_item_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_tool_plan": self.raw_tool_plan,
            "raw_tool_outputs": self.raw_tool_outputs,
            "recommended_item_ids": list(self.recommended_item_ids),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RecBotTrace":
        return cls(
            raw_tool_plan=data.get("raw_tool_plan"),
            raw_tool_outputs=data.get("raw_tool_outputs"),
            recommended_item_ids=list(data.get("recommended_item_ids") or []),
        )


@dataclass
class RecBotTurnResult:
    """Stand-in for ``recbot.types.RecBotTurnResult`` (the run_turn output)."""

    backend: str = "interecagent"
    conversation_id: Optional[str] = None
    turn_id: Optional[str] = None
    user_message: Optional[ChatMessage] = None
    assistant_message: Optional[ChatMessage] = None
    native_action: Optional[NativeAction] = None
    trace: Optional[RecBotTrace] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "backend": self.backend,
            "conversation_id": self.conversation_id,
            "turn_id": self.turn_id,
            "user_message": self.user_message.to_dict() if self.user_message else None,
            "assistant_message": (
                self.assistant_message.to_dict() if self.assistant_message else None
            ),
            "native_action": (
                self.native_action.to_dict() if self.native_action else None
            ),
            "trace": self.trace.to_dict() if self.trace else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RecBotTurnResult":
        na = data.get("native_action")
        tr = data.get("trace")
        um = data.get("user_message")
        am = data.get("assistant_message")
        return cls(
            backend=data.get("backend", "interecagent"),
            conversation_id=data.get("conversation_id"),
            turn_id=data.get("turn_id"),
            user_message=ChatMessage.from_dict(um) if isinstance(um, dict) else None,
            assistant_message=(
                ChatMessage.from_dict(am) if isinstance(am, dict) else None
            ),
            native_action=NativeAction.from_dict(na) if isinstance(na, dict) else None,
            trace=RecBotTrace.from_dict(tr) if isinstance(tr, dict) else None,
        )


def _default_fake_run_turn(request: Any) -> RecBotTurnResult:
    """The default fake turn: a deterministic, fully-populated result.

    Echoes the latest user message, recommends two ids (one resolvable against
    the test catalog, one unknown so id-only rendering is also covered), and
    emits both a structured tool plan and a free-form native ``raw`` string.
    """
    messages = list(getattr(request, "messages", []) or [])
    last_user = ""
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            last_user = str(msg.get("content") or "")
            break
    return RecBotTurnResult(
        backend="interecagent",
        conversation_id=getattr(request, "conversation_id", None),
        turn_id=getattr(request, "turn_id", None) or "turn_fake",
        user_message=ChatMessage("user", last_user),
        assistant_message=ChatMessage(
            "assistant", "Here are a couple of films you might enjoy."
        ),
        native_action=NativeAction(
            raw="HardFilter genre=Sci-Fi, then Rank by match, then Map to ids.",
            raw_tool_plan=[
                {"tool": "HardFilter", "detail": "genre=Sci-Fi"},
                {"tool": "Rank", "detail": "by user match"},
                {"tool": "Map", "detail": "ids"},
            ],
        ),
        trace=RecBotTrace(
            raw_tool_plan=[
                {"tool": "HardFilter", "detail": "genre=Sci-Fi"},
                {"tool": "Rank", "detail": "by user match"},
            ],
            raw_tool_outputs={"candidates": 2},
            recommended_item_ids=["cmu:1", "cmu:unknown"],
        ),
    )


#: The ``sys.modules`` keys the fake owns. Saved/restored as a unit so the fake
#: never leaks out of the backend suite into a sibling suite (e.g. ``recbot/
#: tests``) that needs the *real* ``recbot`` package in the same process.
_FAKE_RECBOT_MODULES = ("recbot", "recbot.types", "recbot.interecagent_bridge")


def _install_fake_recbot() -> types.ModuleType:
    """Install fresh fake ``recbot`` modules into ``sys.modules`` and return the
    fake ``interecagent_bridge``.

    Always builds brand-new module objects (rather than reusing whatever is
    already registered) so the fake is in force regardless of whether the real
    ``recbot`` package was imported earlier in the process. Caller is
    responsible for restoring the previous ``sys.modules`` state afterward (see
    the ``_fake_recbot`` autouse fixture).
    """
    recbot_mod = types.ModuleType("recbot")
    recbot_mod.__path__ = []  # mark as a package
    sys.modules["recbot"] = recbot_mod

    types_mod = types.ModuleType("recbot.types")
    for name, obj in (
        ("ChatMessage", ChatMessage),
        ("RecBotRequest", RecBotRequest),
        ("NativeAction", NativeAction),
        ("RecBotTrace", RecBotTrace),
        ("RecBotTurnResult", RecBotTurnResult),
    ):
        setattr(types_mod, name, obj)
    sys.modules["recbot.types"] = types_mod
    recbot_mod.types = types_mod

    bridge_mod = types.ModuleType("recbot.interecagent_bridge")
    bridge_mod.run_turn = _default_fake_run_turn
    sys.modules["recbot.interecagent_bridge"] = bridge_mod
    recbot_mod.interecagent_bridge = bridge_mod

    return bridge_mod


@pytest.fixture(autouse=True)
def _fake_recbot():
    """Install the fake ``recbot`` backend for the duration of each test.

    The backend service imports ``recbot.types`` / ``recbot.interecagent_bridge``
    **lazily** (inside ``RecBotSession.build_request`` / ``run_turn_sync``), so
    the fake only needs to be present while a test runs, not at collection time.
    Scoping it to each test — and restoring the prior ``sys.modules`` entries on
    teardown — keeps the fake from shadowing the *real* ``recbot`` package when
    this suite is collected alongside ``recbot/tests`` in one ``pytest``
    invocation. The fake is a single stable module object for the whole test, so
    fixtures that monkeypatch ``run_turn`` on it (``set_run_turn``) and the lazy
    service imports all see the same module.
    """
    saved = {name: sys.modules.get(name) for name in _FAKE_RECBOT_MODULES}
    _install_fake_recbot()
    try:
        yield
    finally:
        for name, module in saved.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module


# --------------------------------------------------------------------------- #
# Catalog fixtures
# --------------------------------------------------------------------------- #
#: Catalog rows used across the suite. Stable ids/titles/genres so assertions
#: can be exact. Includes blank/malformed/no-id lines added by the writer.
CATALOG_ROWS: List[Dict[str, Any]] = [
    {
        "item_id": "cmu:1",
        "domain": "movie",
        "title": "Blade Runner",
        "description": "A blade runner hunts replicants in a neon-noir future.",
        "display_text": "Blade Runner (1982)",
        "categories": ["Sci-Fi", "Film-noir", "Thriller"],
        "metadata": {"release_year": 1982},
        "signals": {},
        "source": {"dataset": "cmu"},
    },
    {
        "item_id": "cmu:2",
        "domain": "movie",
        "title": "Casablanca",
        "description": "A wartime romance in Morocco.",
        "display_text": "Casablanca (1942)",
        "categories": ["Romance", "Drama", "War"],
        "metadata": {"release_year": 1942},
    },
    {
        "item_id": "cmu:3",
        "domain": "movie",
        "title": "The Maltese Falcon",
        "description": "A detective chases a priceless statuette.",
        "categories": ["Film-noir", "Mystery", "Detective"],
        "metadata": {"release_year": 1941},
    },
    {
        "item_id": "cmu:4",
        "domain": "movie",
        "title": "Alien",
        "description": "A crew battles a deadly creature aboard a spaceship.",
        "categories": ["Sci-Fi", "Horror"],
        "metadata": {"release_year": 1979},
    },
]


def _write_catalog(path: str, rows: List[Dict[str, Any]]) -> None:
    """Write ``rows`` as JSONL plus blank / malformed / no-id lines.

    The extra junk lines exercise CatalogIndex's tolerance: it must skip them
    and still index exactly ``len(rows)`` items.
    """
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        fh.write("   \n")  # blank line -> skipped
        fh.write("{not valid json}\n")  # malformed -> skipped
        fh.write(json.dumps({"title": "Has no id"}) + "\n")  # no item_id -> skipped


@pytest.fixture()
def catalog_rows() -> List[Dict[str, Any]]:
    """The canonical catalog rows (deep-ish copies are unnecessary; read-only)."""
    return [dict(r) for r in CATALOG_ROWS]


@pytest.fixture()
def catalog_path(tmp_path, catalog_rows) -> str:
    """Path to a freshly written temp ``items.jsonl`` for this test."""
    path = os.path.join(str(tmp_path), "items.jsonl")
    _write_catalog(path, catalog_rows)
    return path


@pytest.fixture()
def catalog(catalog_path):
    """A loaded :class:`CatalogIndex` over the temp catalog."""
    from backend.service.catalog_index import CatalogIndex

    return CatalogIndex(catalog_path)


# --------------------------------------------------------------------------- #
# Persistence isolation
# --------------------------------------------------------------------------- #
@pytest.fixture()
def store_dir(tmp_path, monkeypatch):
    """Redirect the default :class:`SessionStore` base dir into ``tmp_path``.

    Patches ``backend.service.session_store._default_base_dir`` so any
    ``SessionStore()`` constructed with no explicit ``base_dir`` (including the
    one built inside :func:`backend.api.app.create_app`) writes here. Returns
    the directory.
    """
    base = os.path.join(str(tmp_path), "sessions")
    import backend.service.session_store as session_store

    monkeypatch.setattr(session_store, "_default_base_dir", lambda: base)
    return base


@pytest.fixture()
def store(store_dir):
    """A :class:`SessionStore` rooted at the isolated temp dir."""
    from backend.service.session_store import SessionStore

    return SessionStore(base_dir=store_dir)


# --------------------------------------------------------------------------- #
# Service objects
# --------------------------------------------------------------------------- #
@pytest.fixture()
def config_manager():
    """A fresh :class:`ConfigManager`."""
    from backend.service.config import ConfigManager

    return ConfigManager()


@pytest.fixture()
def manager(catalog, store, config_manager):
    """A :class:`SessionManager` wired to the temp catalog + isolated store."""
    from backend.service.session import SessionManager

    mgr = SessionManager(catalog=catalog, store=store, config_manager=config_manager)
    try:
        yield mgr
    finally:
        mgr.shutdown()


# --------------------------------------------------------------------------- #
# run_turn control
# --------------------------------------------------------------------------- #
@pytest.fixture()
def set_run_turn(monkeypatch):
    """Return a setter that swaps the fake ``recbot...run_turn`` for a test.

    The service does ``from recbot.interecagent_bridge import run_turn`` lazily
    at call time, so reassigning the module attribute before the turn runs is
    picked up. ``monkeypatch`` restores the default afterward.
    """
    import recbot.interecagent_bridge as bridge

    def _set(fn):
        monkeypatch.setattr(bridge, "run_turn", fn)
        return fn

    return _set


# --------------------------------------------------------------------------- #
# FastAPI app / client
# --------------------------------------------------------------------------- #
@pytest.fixture()
def app(catalog_path, store_dir):
    """A fresh FastAPI app bound to the temp catalog + isolated store.

    ``store_dir`` is requested (not used directly) so its monkeypatch of the
    session-store base dir is active before ``create_app`` constructs the store.
    """
    from backend.api.app import create_app

    application = create_app(catalog_path=catalog_path)
    try:
        yield application
    finally:
        services = getattr(application.state, "services", None)
        if services is not None:
            services.shutdown()


@pytest.fixture()
def client(app):
    """A ``TestClient`` for the app (context-managed so lifespan hooks fire)."""
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client
