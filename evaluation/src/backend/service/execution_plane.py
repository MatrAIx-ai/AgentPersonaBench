"""Execution plane resolution for Playground launches."""

from __future__ import annotations

import os

EXECUTION_PLANE_ENV = "MATRIX_EXECUTION_PLANE"
REMOTE_RUNNER_API_URL_ENV = "REMOTE_RUNNER_API_URL"
REMOTE_RUNNER_API_KEY_ENV = "REMOTE_RUNNER_API_KEY"

EXECUTION_PLANES = frozenset({"harbor", "remote"})


class ExecutionPlaneError(ValueError):
    """Raised when an execution plane value is invalid or misconfigured."""


def normalize_execution_plane(raw: str | None) -> str:
    value = (raw or "harbor").strip().lower()
    if value not in EXECUTION_PLANES:
        raise ExecutionPlaneError(
            "execution plane must be one of {}".format(sorted(EXECUTION_PLANES))
        )
    return value


def default_execution_plane() -> str:
    """Return the process default execution plane."""
    return normalize_execution_plane(os.environ.get(EXECUTION_PLANE_ENV, "harbor"))


def remote_runner_api_url() -> str:
    return os.environ.get(REMOTE_RUNNER_API_URL_ENV, "").strip()


def remote_runner_configured() -> bool:
    return bool(remote_runner_api_url())
