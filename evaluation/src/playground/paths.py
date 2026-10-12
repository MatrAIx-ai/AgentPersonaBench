"""Path helpers for the extracted Playground core package."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT_ENV = "MATRIX_REPO_ROOT"
PERSONA_DATA_DIR_ENV = "MATRIX_PLAYGROUND_DATA_DIR"


def repo_root_from(start: Path | None = None) -> Path | None:
    override = os.environ.get(REPO_ROOT_ENV, "").strip()
    if override:
        candidate = Path(override).expanduser().resolve()
        if candidate.exists():
            return candidate

    origin = (start or Path(__file__)).resolve()
    for base in (origin, *origin.parents):
        if (base / "application" / "playground").is_dir():
            return base
        if (
            (base / "pyproject.toml").is_file()
            and (base / "application").is_dir()
            and (base / "packages").is_dir()
        ):
            return base
    return None


def persona_data_dir(start: Path | None = None) -> Path:
    override = os.environ.get(PERSONA_DATA_DIR_ENV, "").strip()
    if override:
        return Path(override).expanduser().resolve()

    repo_root = repo_root_from(start)
    if repo_root is not None:
        return repo_root / "persona" / "datasets" / "matraix-persona-dev-sample"

    return Path(__file__).resolve().parents[4] / "persona" / "datasets" / "matraix-persona-dev-sample"
