"""Lightweight persona strategy lookup for Playground setup panels."""

from __future__ import annotations

from pathlib import Path

from backend.service.persona_strategy import load_persona_strategy


def get_task_persona_strategy(task_path: str, *, repo_root: Path) -> dict[str, object] | None:
    normalized = task_path.strip().replace("\\", "/").strip("/")
    if not normalized:
        raise ValueError("task_path must not be empty")
    task_dir = repo_root / normalized
    if not task_dir.is_dir():
        raise FileNotFoundError("task not found: {}".format(normalized))
    return load_persona_strategy(task_dir)
