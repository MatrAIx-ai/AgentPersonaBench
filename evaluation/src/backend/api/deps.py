"""Process-wide service singletons for the Playground API.

The architecture runs a **single** uvicorn worker. This module constructs the
shared service-layer objects and hands them to the FastAPI app / route handlers:

* :class:`~backend.service.config.ConfigManager` — config validation + env mapping.
* :class:`~backend.service.harbor_job_service.HarborJobService` — Harbor batch jobs.
* :class:`~backend.service.persona_pool_service.PersonaPoolService` — persona pool catalog.

Construction is **lazy and cached**: :func:`get_state` builds the singletons on
first use and returns the same :class:`AppState` thereafter.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # pragma: no cover - typing only
    from backend.service.harbor_job_service import HarborJobService
    from backend.service.persona_pool_service import PersonaPoolService

from backend.service.config import ConfigManager

__all__ = [
    "AppState",
    "build_state",
    "get_state",
    "reset_state",
    "state_from_request",
]


@dataclass
class AppState:
    """Container for the process-wide service singletons."""

    config: ConfigManager
    harbor_jobs: "HarborJobService"
    persona_pool: "PersonaPoolService"

    def shutdown(self) -> None:
        """Release background resources."""
        self.harbor_jobs.shutdown()


def build_state(catalog_path: Optional[str] = None) -> AppState:
    """Construct a fresh, fully-wired :class:`AppState`.

    ``catalog_path`` is accepted for backward compatibility with tests but is
    unused — catalog-backed chat sessions were removed from the API surface.
    """
    _ = catalog_path
    config = ConfigManager()
    from backend.service.harbor_job_service import HarborJobService
    from backend.service.persona_pool_service import PersonaPoolService

    harbor_jobs = HarborJobService.from_repo()
    persona_pool = PersonaPoolService.from_repo(repo_root=harbor_jobs.repo_root)
    return AppState(
        config=config,
        harbor_jobs=harbor_jobs,
        persona_pool=persona_pool,
    )


_state: Optional[AppState] = None
_state_lock = threading.Lock()


def get_state(catalog_path: Optional[str] = None) -> AppState:
    """Return the process-wide :class:`AppState`, constructing it on first use."""
    global _state
    if _state is None:
        with _state_lock:
            if _state is None:
                _state = build_state(catalog_path)
    return _state


def reset_state() -> None:
    """Drop the cached singleton (shutting down its job pool)."""
    global _state
    with _state_lock:
        if _state is not None:
            try:
                _state.shutdown()
            except Exception:  # pragma: no cover - best-effort cleanup
                pass
        _state = None


def state_from_request(request) -> AppState:
    """Resolve the :class:`AppState` for a request."""
    services = getattr(request.app.state, "services", None)
    if isinstance(services, AppState):
        return services
    return get_state()
