"""Load task-owned self-report schema metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from playground.task_content_bundle import (
    content_dir_for_task_path,
    input_dir_for_task_path,
    task_dir_from_path,
)
from playground.user_sim.self_report_contract import (
    DEFAULT_CHATBOT_SELF_REPORT_SCHEMA,
    SelfReportField,
    SelfReportSchema,
    schema_prompt_block,
)


def _as_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_string(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _as_optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _read_schema_yaml(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("self_report_schema.yaml must be a mapping")
    return dict(payload)


def _normalize_enum_choice(choice: Any) -> str:
    """YAML 1.1 parses bare ``yes``/``no`` as booleans — restore enum tokens."""
    if isinstance(choice, bool):
        return "yes" if choice else "no"
    return str(choice or "").strip()


def _normalize_enum_choices(raw_choices: Any) -> tuple[str, ...]:
    choices = tuple(
        token
        for token in (_normalize_enum_choice(choice) for choice in (raw_choices or []))
        if token
    )
    lowered = [token.lower() for token in choices]
    # Already-stringified bools from a prior bad load: True/partially/False.
    if "partially" in lowered and "true" in lowered and "false" in lowered:
        return tuple(
            "yes"
            if token.lower() == "true"
            else "no"
            if token.lower() == "false"
            else token
            for token in choices
        )
    return choices


def _field_from_item(
    item: dict[str, Any], index: int, *, explains: str | None = None
) -> SelfReportField:
    key = _as_string(item.get("key"))
    prompt = _as_string(item.get("prompt"))
    if not key or not prompt:
        raise ValueError(
            "self_report_schema.fields[{}] requires key and prompt".format(index)
        )
    choices = _normalize_enum_choices(item.get("choices") or [])
    return SelfReportField(
        key=key,
        prompt=prompt,
        kind=_as_string(item.get("kind")) or "string",
        required=_as_bool(item.get("required"), True),
        minimum=_as_optional_int(item.get("minimum")),
        maximum=_as_optional_int(item.get("maximum")),
        choices=choices,
        explains=explains or (_as_string(item.get("explains")) or None),
    )


def _explanation_blocks(item: dict[str, Any]) -> list[dict[str, Any]]:
    """Inline ``explanation`` sub-field(s) authored under a measured field."""
    raw = item.get("explanation")
    if isinstance(raw, dict):
        return [_as_mapping(raw)]
    if isinstance(raw, list):
        return [_as_mapping(block) for block in raw if isinstance(block, dict)]
    return []


def _load_schema_from_payload(payload: dict[str, Any]) -> SelfReportSchema:
    fields = []
    for index, entry in enumerate(payload.get("fields") or []):
        item = _as_mapping(entry)
        parent = _field_from_item(item, index)
        fields.append(parent)
        # An ``explanation`` sub-block is authoring sugar for a flat textual field
        # bound to its parent — the binding drives reporting's group-by axis.
        for block in _explanation_blocks(item):
            fields.append(_field_from_item(block, index, explains=parent.key))
    return SelfReportSchema(
        artifact_name=_as_string(payload.get("artifactName")) or "user_feedback.json",
        instructions=_as_string(payload.get("instructions")),
        fields=tuple(fields),
    )


def load_self_report_schema_for_task_path(
    task_path: str,
    *,
    repo_root: Path,
    fallback_to_default: bool = True,
) -> SelfReportSchema | None:
    task_dir = task_dir_from_path(task_path, repo_root=repo_root)
    input_dir = input_dir_for_task_path(task_path, repo_root=repo_root)
    content_dir = content_dir_for_task_path(task_path, repo_root=repo_root)
    candidates: list[Path] = []
    if input_dir is not None:
        candidates.append(input_dir / "self_report_schema.yaml")
    candidates.append(task_dir / "self_report_schema.yaml")
    if content_dir is not None:
        candidates.append(content_dir / "self_report_schema.yaml")
    for candidate in candidates:
        payload = _read_schema_yaml(candidate)
        if payload is not None:
            return _load_schema_from_payload(payload)
    if fallback_to_default:
        return DEFAULT_CHATBOT_SELF_REPORT_SCHEMA
    return None


def render_self_report_schema_markdown(schema: SelfReportSchema) -> str:
    """Human-readable self-report contract for cockpit task detail panels."""
    parts = [
        "Platform-managed harness artifacts are documented in "
        "`application/task-spec/chatbot/eval_artifacts.md`.",
        "",
        "Persona self-report artifact: `{}`".format(schema.artifact_name),
    ]
    if schema.instructions.strip():
        parts.extend(["", schema.instructions.strip()])
    parts.extend(["", schema_prompt_block(schema)])
    return "\n".join(parts).strip()


def render_task_self_report_preview_markdown(schema: SelfReportSchema) -> str:
    """Render task-owned ``self_report_schema.yaml`` for contributor preview."""
    parts: list[str] = []
    if schema.instructions.strip():
        parts.append(schema.instructions.strip())
    artifact = schema.artifact_name.strip() or "user_feedback.json"
    parts.extend(["", "Artifact: `{}`".format(artifact), "", schema_prompt_block(schema)])
    return "\n".join(parts).strip()
