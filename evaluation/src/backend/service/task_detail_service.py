"""Read Harbor task docs for cockpit detail panels."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from backend.service.application_types import normalize_metadata_type
from playground.task_content_bundle import (
    load_task_content_bundle_for_task_path,
)


def _humanize_key(value: str) -> str:
    text = str(value).replace("_", " ").strip()
    if not text:
        return text
    return " ".join(word.capitalize() for word in text.split(" "))


def _read_instruction_meta(instruction_path: Path) -> tuple[str, str]:
    if not instruction_path.is_file():
        return "", ""
    title = ""
    description = ""
    for line in instruction_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and not title:
            title = stripped.lstrip("# ").strip()
            continue
        if title and not description and stripped and not stripped.startswith("#"):
            description = stripped
            break
    return title, description


def get_task_detail(task_path: str, *, repo_root: Path) -> dict[str, Any]:
    normalized = task_path.strip().replace("\\", "/").strip("/")
    if not normalized:
        raise ValueError("task_path must not be empty")
    task_dir = repo_root / normalized
    if not task_dir.is_dir():
        raise FileNotFoundError("task not found: {}".format(normalized))

    instruction_path = task_dir / "instruction.md"
    instruction_md = (
        instruction_path.read_text(encoding="utf-8").strip() if instruction_path.is_file() else ""
    )
    instruction_title, instruction_blurb = _read_instruction_meta(instruction_path)

    extra_docs: list[dict[str, str]] = []
    for name in ("README.md",):
        doc_path = task_dir / name
        if doc_path.is_file():
            extra_docs.append(
                {
                    "name": name,
                    "content": doc_path.read_text(encoding="utf-8").strip(),
                }
            )

    meta_type = ""
    domain = ""
    difficulty = ""
    tags: list[str] = []
    task_name = task_dir.name
    toml_path = task_dir / "task.toml"
    if toml_path.is_file():
        raw = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        meta = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
        meta_type = normalize_metadata_type(str(meta.get("type") or ""))
        domain = str(meta.get("domain") or "").strip()
        difficulty = str(meta.get("difficulty") or "").strip()
        raw_tags = meta.get("tags")
        if isinstance(raw_tags, list):
            tags = [str(item) for item in raw_tags if str(item).strip()]
        task_block = raw.get("task") if isinstance(raw.get("task"), dict) else {}
        task_name = str(task_block.get("name") or task_name)

    from backend.service.application_task_metadata import title_from_harbor_task_name
    from backend.service.persona_strategy import load_persona_strategy

    title = title_from_harbor_task_name(task_name) or _humanize_key(task_dir.name.replace("-", " "))
    description = instruction_blurb
    persona_strategy = load_persona_strategy(task_dir)
    bundle = load_task_content_bundle_for_task_path(normalized, repo_root=repo_root)
    if bundle.instruction_markdown.strip():
        instruction_md = bundle.instruction_markdown.strip()
    context_markdown = ""
    questionnaire_markdown = ""
    output_schema_markdown = bundle.output_schema_markdown.strip()
    self_report_markdown = ""
    questionnaire = None
    if bundle.context_markdown.strip():
        context_markdown = bundle.context_markdown.strip()
    if meta_type in {"chatbot", "web", "os-app"}:
        output_schema_markdown = ""
        try:
            from playground.self_report_task_config import (
                load_self_report_schema_for_task_path,
                render_task_self_report_preview_markdown,
            )

            schema = load_self_report_schema_for_task_path(
                normalized,
                repo_root=repo_root,
                fallback_to_default=False,
            )
            if schema is not None:
                self_report_markdown = render_task_self_report_preview_markdown(schema)
        except Exception:  # noqa: BLE001
            self_report_markdown = ""
    elif meta_type == "survey":
        questionnaire_id = None
        try:
            from backend.service.survey_questionnaire_catalog import get_survey_questionnaire
            from backend.service.survey_task_registry import survey_questionnaire_id_for_task_path
            from playground.survey_task_content import (
                load_survey_task_content_for_task_path,
            )

            questionnaire_id = survey_questionnaire_id_for_task_path(normalized)
            fallback_questionnaire = (
                get_survey_questionnaire(questionnaire_id, repo_root=repo_root)
                if questionnaire_id
                else None
            )
            content = load_survey_task_content_for_task_path(
                normalized,
                repo_root=repo_root,
                questionnaire_id=questionnaire_id,
                fallback_questionnaire=fallback_questionnaire,
            )
            if content.instruction_markdown.strip():
                instruction_md = content.instruction_markdown.strip()
            context_markdown = content.context_markdown.strip()
            questionnaire_markdown = content.questionnaire_markdown.strip()
            output_schema_markdown = content.output_schema_markdown.strip()
            questionnaire = content.instrument.to_dict() if content.instrument is not None else None
            if not description:
                description = (
                    (content.context_markdown or instruction_blurb or "").strip().splitlines()[0]
                    if (content.context_markdown or instruction_blurb)
                    else ""
                )
            # Keep ``[task].name``-derived title; do not overwrite with questionnaire title.
        except Exception:  # noqa: BLE001
            questionnaire_markdown = ""
            questionnaire = None

    markdown_parts = [f"# {title}", ""]
    if description:
        markdown_parts.extend([description, ""])
    markdown_parts.append(f"**Harbor path:** `{normalized}`")
    if meta_type:
        markdown_parts.append(f"**Type:** `{meta_type}`")
    if task_name and task_name != task_dir.name:
        markdown_parts.append(f"**Task name:** `{task_name}`")
    markdown_parts.append("")
    if instruction_md:
        markdown_parts.extend(["---", "", instruction_md])
    if context_markdown:
        markdown_parts.extend(["", "---", "", "## Context", "", context_markdown])
    if questionnaire_markdown:
        markdown_parts.extend(["", "---", "", "## Questionnaire", "", questionnaire_markdown])
    if output_schema_markdown:
        markdown_parts.extend(["", "---", "", "## Answer envelope", "", output_schema_markdown])
    if self_report_markdown:
        markdown_parts.extend(["", "---", "", "## Persona self-report", "", self_report_markdown])
    for doc in extra_docs:
        if doc["name"] in {"instruction.md", "README.md"}:
            continue
        markdown_parts.extend(["", "---", "", f"## {doc['name']}", ""])
        if doc["name"].endswith(".md"):
            markdown_parts.append(doc["content"])
        else:
            markdown_parts.extend(["```yaml", doc["content"], "```"])

    return {
        "taskPath": normalized,
        "title": title,
        "description": description,
        "metaType": meta_type,
        "taskName": task_name,
        "domain": domain,
        "difficulty": difficulty,
        "tags": tags,
        "instructionMarkdown": instruction_md,
        "contextMarkdown": context_markdown,
        "questionnaireMarkdown": questionnaire_markdown,
        "outputSchemaMarkdown": output_schema_markdown,
        "selfReportMarkdown": self_report_markdown,
        "questionnaire": questionnaire,
        "personaStrategy": persona_strategy,
        "profileMarkdown": "\n".join(markdown_parts).strip(),
        "extraDocs": extra_docs,
    }


def attach_task_profile_markdown(
    payload: dict[str, Any],
    *,
    repo_root: Path,
) -> dict[str, Any]:
    """Add ``profileMarkdown`` to a task dict when ``taskPath`` is known."""
    task_path = str(payload.get("taskPath") or payload.get("task_path") or "").strip()
    if not task_path:
        return payload
    try:
        detail = get_task_detail(task_path, repo_root=repo_root)
    except (FileNotFoundError, ValueError, OSError):
        return payload
    merged = dict(payload)
    merged["profileMarkdown"] = detail.get("profileMarkdown") or ""
    merged["instructionMarkdown"] = detail.get("instructionMarkdown") or ""
    merged["contextMarkdown"] = detail.get("contextMarkdown") or ""
    merged["questionnaireMarkdown"] = detail.get("questionnaireMarkdown") or ""
    merged["outputSchemaMarkdown"] = detail.get("outputSchemaMarkdown") or ""
    merged["selfReportMarkdown"] = detail.get("selfReportMarkdown") or ""
    merged["questionnaire"] = detail.get("questionnaire")
    return merged
