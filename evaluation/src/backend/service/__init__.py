"""Service-layer utilities for Playground."""

from __future__ import annotations

from pathlib import Path

__all__ = ["ensure_recbot_importable"]


def ensure_recbot_importable() -> str:
    """Compatibility shim for older API startup code.

    The RecAI sidecar and task tree are no longer shipped, so there is no
    task-owned ``recbot`` package to inject into ``sys.path``.
    """
    return str(Path(__file__).resolve().parents[4])
