"""FastAPI application layer for Playground.

This package exposes the HTTP API that the React SPA talks to. It is a thin
adapter over the pure-python service layer (:mod:`backend.service`):

* :mod:`~backend.api.schemas` -- pydantic v2 request/response models that mirror
  the wire contract documented in the README and the TypeScript types.
* :mod:`~backend.api.jobs` -- an in-memory :class:`JobRegistry` that runs a
  blocking turn in a threadpool under the session's per-session
  :class:`asyncio.Lock`, exposing a ``building -> running -> done | error``
  lifecycle so the UI can poll.
* :mod:`~backend.api.routes` -- the ``/api`` router wiring every endpoint to the
  :class:`~backend.service.session.SessionManager` /
  :class:`~backend.service.catalog_index.CatalogIndex`.
* :mod:`~backend.api.app` -- the :class:`fastapi.FastAPI` app: CORS for the Vite
  dev server, the router, and (when built) the static SPA mounted at ``/``.

Importing this package is cheap and side-effect-light: it does NOT import RecAI,
numpy, or pandas. The heavyweight :func:`recbot.interecagent_bridge.run_turn` is
imported lazily inside :meth:`backend.service.session.RecBotSession.run_turn_sync`
only when a turn actually executes, so the API (and its tests) run with just
FastAPI + pydantic installed.
"""

from __future__ import annotations

# Importing the service package wires
# the task-owned chatbot API source onto ``sys.path`` (so ``import recbot...``
# resolves) without importing recbot itself. Doing it here means
# simply importing ``backend.api`` is enough to make the lazy backend import
# work later.
from backend.service import ensure_recbot_importable

__all__ = ["ensure_recbot_importable"]

ensure_recbot_importable()
