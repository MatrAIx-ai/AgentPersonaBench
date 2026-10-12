"""Load canonical task-owned content docs for application tasks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.service.task_environment import resolve_task_environment_dir


@dataclass
class TaskContentBundle:
    instruction_markdown: str = ""
    context_markdown: str = ""
    output_schema_markdown: str = ""


def task_dir_from_path(task_path: str, *, repo_root: Path) -> Path:
    return (repo_root / task_path.strip().replace("\\", "/")).resolve()


def input_dir_for_task_path(task_path: str, *, repo_root: Path) -> Path | None:
    task_dir = task_dir_from_path(task_path, repo_root=repo_root)
    if not task_dir.is_dir():
        return None
    input_dir = task_dir / "input"
    return input_dir if input_dir.is_dir() else None


def content_dir_for_task_path(task_path: str, *, repo_root: Path) -> Path | None:
    task_dir = task_dir_from_path(task_path, repo_root=repo_root)
    if not task_dir.is_dir():
        return None
    environment_dir = resolve_task_environment_dir(task_dir)
    # Shared environments provide runtime capabilities only. Contributor-facing
    # task docs should live under the task folder itself.
    if environment_dir.name.startswith("shared-"):
        return None
    content_dir = environment_dir / "content"
    if content_dir.is_dir():
        return content_dir
    if environment_dir.is_dir():
        return environment_dir
    return None


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").strip()


def load_task_content_bundle_for_task_path(
    task_path: str,
    *,
    repo_root: Path,
) -> TaskContentBundle:
    input_dir = input_dir_for_task_path(task_path, repo_root=repo_root)
    content_dir = content_dir_for_task_path(task_path, repo_root=repo_root)
    task_dir = task_dir_from_path(task_path, repo_root=repo_root)
    instruction_markdown = _read_text(task_dir / "instruction.md")
    context_markdown = ""
    output_schema_markdown = ""
    if input_dir is not None:
        context_markdown = _read_text(input_dir / "context.md")
        output_schema_markdown = _read_text(input_dir / "output_schema.md")
    if content_dir is not None:
        context_markdown = context_markdown or _read_text(content_dir / "context.md")
        output_schema_markdown = output_schema_markdown or _read_text(
            content_dir / "output_schema.md"
        )
    return TaskContentBundle(
        instruction_markdown=instruction_markdown,
        context_markdown=context_markdown,
        output_schema_markdown=output_schema_markdown,
    )
