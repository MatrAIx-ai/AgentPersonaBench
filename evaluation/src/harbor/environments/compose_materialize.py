"""Materialize a persona agent env plus optional local endpoint compose."""

from __future__ import annotations

import shutil
from pathlib import Path, PurePosixPath


def normalize_task_environments_ref(value: str, *, field_name: str) -> str:
    clean = value.strip()
    posix_path = PurePosixPath(clean)
    if (
        not clean
        or "\\" in clean
        or posix_path.is_absolute()
        or any(part in {"", ".", ".."} for part in posix_path.parts)
    ):
        raise ValueError(
            f"[environment].{field_name} must be a relative POSIX path under "
            "environment/task-environments."
        )
    return posix_path.as_posix()


def resolve_task_environments_path(repo_root: Path, ref: str) -> Path:
    return (
        repo_root / "evaluation" / "src" / "environment" / "task-environments" / ref
    ).resolve()


def materialize_persona_with_local_compose(
    *,
    persona_dir: Path,
    local_compose_dir: Path,
    dest_dir: Path,
) -> Path:
    """Copy persona agent files and local endpoint compose into one directory.

    Harbor Docker / DinD trials must upload a single self-contained environment
    directory. When a chat task opts into a local endpoint host, materialize
    both trees into ``dest_dir`` before compose starts.
    """
    persona_dir = persona_dir.resolve()
    local_compose_dir = local_compose_dir.resolve()
    dest_dir = dest_dir.resolve()

    if not persona_dir.is_dir():
        raise FileNotFoundError(f"persona environment not found: {persona_dir}")
    if not local_compose_dir.is_dir():
        raise FileNotFoundError(f"local compose package not found: {local_compose_dir}")

    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    for name in ("Dockerfile", "install-claude-code.sh"):
        source = persona_dir / name
        if source.is_file():
            shutil.copy2(source, dest_dir / name)

    compose_source = local_compose_dir / "docker-compose.yaml"
    if not compose_source.is_file():
        raise FileNotFoundError(
            f"local compose package missing docker-compose.yaml: {local_compose_dir}"
        )
    shutil.copy2(compose_source, dest_dir / "docker-compose.yaml")

    for child in local_compose_dir.iterdir():
        # Skip the Harbor compose (already copied) and helper/dot dirs such as
        # ``.playground_sidecar`` (host-only standalone compose for Playground).
        if child.name == "docker-compose.yaml" or child.name.startswith("."):
            continue
        target = dest_dir / child.name
        if child.is_dir():
            shutil.copytree(child, target, dirs_exist_ok=True)
        elif child.is_file():
            shutil.copy2(child, target)

    return dest_dir
