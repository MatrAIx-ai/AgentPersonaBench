from __future__ import annotations

import tomllib
from pathlib import Path, PurePosixPath


TASK_ENVIRONMENTS_ROOT = Path("evaluation") / "src" / "environment" / "task-environments"


def resolve_task_environment_dir(task_dir: Path) -> Path:
    """Resolve a task's runtime environment directory.

    The Harbor runtime owns the canonical resolver. This fallback keeps the
    Playground app importable from source before Harbor is on PYTHONPATH.
    """
    try:
        from harbor.models.task.paths import TaskPaths

        return TaskPaths.from_task_dir(task_dir).environment_dir
    except (ModuleNotFoundError, AttributeError):
        # Installed Harbor wheels may lag the in-repo TaskPaths API.
        return _resolve_without_harbor(task_dir)


def resolve_task_local_compose_dir(task_dir: Path) -> Path | None:
    """Resolve optional ``[environment].local_compose`` under task-environments."""
    task_dir = task_dir.resolve()
    ref = _read_environment_field(task_dir / "task.toml", "local_compose")
    if ref is None:
        return None
    repo_root = _repo_root_for_task(task_dir)
    if repo_root is None:
        return None
    path = (repo_root / TASK_ENVIRONMENTS_ROOT / ref).resolve()
    return path if path.is_dir() else None


def resolve_chat_endpoint_host_dir(task_dir: Path) -> Path | None:
    """Directory that hosts a local chat endpoint (sidecar package or env dir)."""
    local_compose = resolve_task_local_compose_dir(task_dir)
    if local_compose is not None:
        return local_compose
    environment_dir = resolve_task_environment_dir(task_dir)
    return environment_dir if environment_dir.is_dir() else None


def _resolve_without_harbor(task_dir: Path) -> Path:
    task_dir = task_dir.resolve()
    local_environment_dir = task_dir / "environment"
    if local_environment_dir.exists():
        return local_environment_dir

    definition = _read_environment_field(task_dir / "task.toml", "definition")
    if definition is None:
        return local_environment_dir

    repo_root = _repo_root_for_task(task_dir)
    if repo_root is None:
        return local_environment_dir
    return (repo_root / TASK_ENVIRONMENTS_ROOT / definition).resolve()


def _read_environment_field(config_path: Path, field: str) -> str | None:
    try:
        raw_config = tomllib.loads(config_path.read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return None

    raw_environment = raw_config.get("environment")
    if not isinstance(raw_environment, dict):
        return None
    value = raw_environment.get(field)
    if not isinstance(value, str):
        return None

    clean = value.strip()
    posix_path = PurePosixPath(clean)
    if (
        not clean
        or "\\" in clean
        or posix_path.is_absolute()
        or any(part in {"", ".", ".."} for part in posix_path.parts)
    ):
        return None
    return posix_path.as_posix()


def _repo_root_for_task(task_dir: Path) -> Path | None:
    for candidate in (task_dir, *task_dir.parents):
        if (candidate / TASK_ENVIRONMENTS_ROOT).exists():
            return candidate
        if (candidate / "pyproject.toml").exists():
            return candidate
    return None
