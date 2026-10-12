"""Read Harbor-standard task metadata from ``application/tasks/*/task.toml``."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from backend.service.application_types import CANONICAL_APPLICATION_TYPES, normalize_metadata_type
from backend.service.playground_task_registry import (
    PlaygroundTaskEntry,
    default_environment_label,
    default_os_app_backend,
    default_os_app_platform,
    get_playground_entry,
    resolve_task_kind,
)


@dataclass(frozen=True)
class ApplicationTaskRecord:
    folder_name: str
    task_path: str
    task_name: str
    title: str
    description: str
    meta_type: str
    os: str
    domain: str
    difficulty: str
    tags: List[str] = field(default_factory=list)
    playground: PlaygroundTaskEntry | None = None
    task_kind: str = "task"


def _as_str_list(value: object) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def parse_task_toml(task_dir: Path) -> Dict[str, object]:
    toml_path = task_dir / "task.toml"
    if not toml_path.is_file():
        return {}
    return tomllib.loads(toml_path.read_text(encoding="utf-8"))


def read_instruction_meta(instruction_path: Path) -> tuple[str, str]:
    if not instruction_path.is_file():
        return "", ""
    title = ""
    desc_lines: list[str] = []
    for line in instruction_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and not title:
            title = stripped.lstrip("# ").strip()
            continue
        if title and not desc_lines and not stripped:
            continue
        if title and stripped and not stripped.startswith("#"):
            desc_lines.append(stripped)
            continue
        if desc_lines:
            break
    return title, " ".join(desc_lines)


def humanize_folder(folder_name: str) -> str:
    import re

    stem = folder_name
    for prefix in ("example-survey_", "survey_", "example-"):
        if stem.startswith(prefix):
            stem = stem[len(prefix) :]
            break
    stem = re.sub(r"^(web|computer-use)-", "", stem)
    stem = stem.replace("_", " ").replace("-", " ")
    return stem.strip().title() or folder_name


def slug_from_harbor_task_name(task_name: str) -> str:
    """Return the slug portion of ``[task].name``."""
    raw = task_name.strip()
    if not raw:
        return ""
    lowered = raw.lower()
    if lowered.startswith("application/"):
        return raw.split("/", 1)[1]
    legacy = "matraix/application-"
    if lowered.startswith(legacy):
        return raw[len(legacy) :]
    if "/" in raw:
        return raw.rsplit("/", 1)[-1]
    return raw


# ``[task].name`` slugs embed the application type (``survey-…``, ``chat-…``);
# drop it from display titles since ``metadata.type`` already carries it.
_TITLE_TYPE_PREFIXES = (
    "computer-use-macos-",
    "computer-use-ios-",
    "computer-use-linux-",
    "computer-use-",
    "os-app-macos-",
    "os-app-ios-",
    "os-app-linux-",
    "os-app-",
    "survey-",
    "chatbot-",
    "chat-",
    "web-",
)

# Known acronyms / product names that plain ``str.capitalize`` mangles.
_TITLE_WORD_OVERRIDES = {
    "ai": "AI",
    "api": "API",
    "mcp": "MCP",
    "csv": "CSV",
    "ios": "iOS",
    "macos": "macOS",
    "openbb": "OpenBB",
    "cfpb": "CFPB",
    "fdic": "FDIC",
    "cps": "CPS",
    "cvs": "CVS",
    "sppa": "SPPA",
    "tus": "TUS",
    "mu": "MU",
    "vscode": "VSCode",
}


def title_from_harbor_task_name(task_name: str) -> str:
    """Derive UI title from ``[task].name`` (``application/<slug>``)."""
    slug = slug_from_harbor_task_name(task_name).replace("_", "-")
    for prefix in _TITLE_TYPE_PREFIXES:
        if slug.startswith(prefix) and len(slug) > len(prefix):
            slug = slug[len(prefix) :]
            break
    words = [word for word in slug.split("-") if word]
    if not words:
        return ""
    return " ".join(_TITLE_WORD_OVERRIDES.get(word.lower(), word.capitalize()) for word in words)


def infer_playground_entry(
    folder_name: str,
    *,
    meta_type: str,
    os: str,
) -> PlaygroundTaskEntry | None:
    """Build a default Playground routing entry from Harbor ``metadata.type``."""
    if meta_type not in CANONICAL_APPLICATION_TYPES:
        return None
    if meta_type == "survey":
        return PlaygroundTaskEntry(application_type="survey")
    if meta_type == "chatbot":
        return PlaygroundTaskEntry(application_type="chatbot")
    if meta_type == "web":
        return PlaygroundTaskEntry(application_type="web")
    pe = PlaygroundTaskEntry(application_type="os-app")
    os_app_backend = default_os_app_backend(meta_type, pe, os)
    os_app_platform = default_os_app_platform(meta_type, os_app_backend, os)
    return PlaygroundTaskEntry(
        application_type="os-app",
        os_app_backend=os_app_backend,
        os_app_platform=os_app_platform,
        environment_label=default_environment_label(os_app_platform),
    )


def resolve_playground_entry(
    folder_name: str,
    *,
    meta_type: str,
    os: str,
) -> PlaygroundTaskEntry | None:
    """Return registry override or inferred Playground entry for a task folder."""
    return get_playground_entry(folder_name) or infer_playground_entry(
        folder_name,
        meta_type=meta_type,
        os=os,
    )


def parse_application_task(task_dir: Path) -> ApplicationTaskRecord | None:
    raw = parse_task_toml(task_dir)
    if not raw:
        return None

    folder_name = task_dir.name
    meta = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    meta_type = normalize_metadata_type(str(meta.get("type") or ""))
    os = str(meta.get("os") or "").strip().lower()
    playground = resolve_playground_entry(folder_name, meta_type=meta_type, os=os)
    if playground is None:
        return None

    domain = str(meta.get("domain") or "").strip()
    difficulty = str(meta.get("difficulty") or "easy").strip()
    tags = _as_str_list(meta.get("tags"))

    task_block = raw.get("task") if isinstance(raw.get("task"), dict) else {}
    task_name = str(task_block.get("name") or "").strip() or f"application/{folder_name.replace('_', '-')}"
    _, instruction_description = read_instruction_meta(task_dir / "instruction.md")
    # Display title always comes from ``[task].name``, not instruction H1.
    title = title_from_harbor_task_name(task_name) or humanize_folder(folder_name)
    description = instruction_description or f"Harbor task ({folder_name})."

    return ApplicationTaskRecord(
        folder_name=folder_name,
        task_path="application/tasks/{}".format(folder_name),
        task_name=task_name,
        title=title,
        description=description,
        meta_type=meta_type,
        os=os,
        domain=domain,
        difficulty=difficulty,
        tags=tags,
        playground=playground,
        task_kind=resolve_task_kind(folder_name, playground),
    )
