"""Lightweight survey questionnaire metadata for task list endpoints."""

from __future__ import annotations

from pathlib import Path

import yaml


def read_survey_questionnaire_list_meta(task_dir: Path) -> tuple[str | None, int | None]:
    """Return ``(questionnaire_id, question_count)`` without markdown rendering."""
    for relative in ("input/questionnaire.yaml", "content/questionnaire.yaml"):
        yaml_path = task_dir / relative
        if not yaml_path.is_file():
            continue
        try:
            payload = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            return None, None
        if not isinstance(payload, dict):
            return None, None
        questionnaire_id = str(payload.get("id") or "").strip() or None
        questions = payload.get("questions")
        question_count = len(questions) if isinstance(questions, list) else None
        return questionnaire_id, question_count
    return None, None
