"""In-memory cache for Playground per-type task registries."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, TypeVar

from backend.service.application_task_index import tasks_dir_signature

_REPO_ROOT = Path(__file__).resolve().parents[4]
_TASKS_DIR = _REPO_ROOT / "application" / "tasks"

T = TypeVar("T")

_REGISTRY_CACHE: Dict[str, tuple[str, object]] = {}


def get_cached_registry(cache_name: str, build: Callable[[], T]) -> T:
    """Return ``build()`` result, reusing it until ``application/tasks`` changes."""
    signature = tasks_dir_signature(_TASKS_DIR)
    cached = _REGISTRY_CACHE.get(cache_name)
    if cached is not None and cached[0] == signature:
        return cached[1]  # type: ignore[return-value]
    value = build()
    _REGISTRY_CACHE[cache_name] = (signature, value)
    return value


def clear_playground_task_registry_cache() -> None:
    """Test helper: drop cached Playground task registries."""
    _REGISTRY_CACHE.clear()
