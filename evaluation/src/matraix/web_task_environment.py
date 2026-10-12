"""Web task Docker environment resolution for CLI harness overrides."""

from __future__ import annotations

import hashlib
import re
import shutil
import tomllib
from pathlib import Path

SHARED_WEB_CLI_DEFINITION = "application/shared-web-cli"

CLI_WEB_HARNESS_NAMES = frozenset(
    {
        "persona-claude-code",
        "persona-codex",
        "persona-gemini-cli",
    }
)

_DEFINITION_PATTERN = re.compile(
    r'(^[\t ]*definition[\t ]*=[\t ]*")([^"]+)(")',
    re.MULTILINE,
)


def is_cli_web_harness(agent_name: str | None) -> bool:
    return (agent_name or "").strip() in CLI_WEB_HARNESS_NAMES


def _resolve_task_dir(task_path: str, repo_root: Path) -> Path:
    normalized = task_path.strip().replace("\\", "/")
    candidate = Path(normalized)
    if candidate.is_absolute():
        task_dir = candidate if candidate.is_dir() else candidate.parent
    else:
        task_dir = (repo_root / normalized).resolve()
    if not task_dir.is_dir():
        raise FileNotFoundError(f"task directory not found: {task_dir}")
    return task_dir


def _read_task_metadata_type(task_dir: Path) -> str | None:
    toml_path = task_dir / "task.toml"
    if not toml_path.is_file():
        return None
    try:
        payload = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    metadata = payload.get("metadata")
    if isinstance(metadata, dict) and metadata.get("type"):
        return str(metadata["type"])
    task = payload.get("task")
    if isinstance(task, dict) and task.get("type"):
        return str(task["type"])
    return None


def _normalize_task_type(task_type: str | None) -> str | None:
    if not task_type:
        return None
    normalized = task_type.strip().lower()
    if normalized in {"chat", "chatbot"}:
        return "chatbot"
    if normalized in {"cua", "computer-use", "computer_use", "os_app", "os-app"}:
        return "os-app"
    return normalized


def _patch_environment_definition(toml_text: str, definition: str) -> str:
    if _DEFINITION_PATTERN.search(toml_text):
        return _DEFINITION_PATTERN.sub(
            rf'\1{definition}\3',
            toml_text,
            count=1,
        )
    raise ValueError("task.toml is missing [environment].definition")


def _staging_cache_key(task_dir: Path) -> str:
    toml_path = task_dir / "task.toml"
    digest = hashlib.sha256()
    digest.update(str(task_dir.resolve()).encode())
    if toml_path.is_file():
        digest.update(toml_path.read_bytes())
    digest.update(SHARED_WEB_CLI_DEFINITION.encode())
    return digest.hexdigest()[:16]


def stage_web_task_for_cli_harness(
    task_dir: Path,
    *,
    cache_dir: Path,
    definition: str = SHARED_WEB_CLI_DEFINITION,
) -> Path:
    """Copy a web task and point ``[environment].definition`` at the CLI image."""
    task_dir = task_dir.resolve()
    cache_dir = cache_dir.resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    staged = cache_dir / task_dir.name / _staging_cache_key(task_dir)

    if staged.is_dir() and (staged / "task.toml").is_file():
        current = (staged / "task.toml").read_text(encoding="utf-8")
        if f'definition = "{definition}"' in current or f'definition="{definition}"' in current:
            return staged

    if staged.exists():
        shutil.rmtree(staged)

    def _ignore(_dir: str, names: list[str]) -> set[str]:
        ignored = {"environment"}
        if staged.exists() and ".staging" in names:
            ignored.add(".staging")
        return ignored

    shutil.copytree(task_dir, staged, ignore=_ignore)
    toml_path = staged / "task.toml"
    patched = _patch_environment_definition(toml_path.read_text(encoding="utf-8"), definition)
    toml_path.write_text(patched, encoding="utf-8")
    return staged


def resolve_web_harbor_task_path(
    task_path: str,
    *,
    agent_name: str | None,
    repo_root: Path,
    cache_dir: Path | None = None,
) -> str:
    """Return Harbor task path, staging under cache when web + CLI harness."""
    normalized = task_path.strip().replace("\\", "/")
    if not is_cli_web_harness(agent_name):
        return normalized

    task_dir = _resolve_task_dir(normalized, repo_root)
    task_type = _normalize_task_type(_read_task_metadata_type(task_dir))
    if task_type != "web":
        return normalized

    staging_root = cache_dir or (repo_root / "data" / "cache" / "playground" / "web_cli_staged_tasks")
    staged = stage_web_task_for_cli_harness(task_dir, cache_dir=staging_root)
    return staged.relative_to(repo_root.resolve()).as_posix()
