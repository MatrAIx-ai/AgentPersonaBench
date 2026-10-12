"""Harbor example-survey task types for Playground."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class SurveyHarborTask:
    id: str
    title: str
    description: str
    task_path: str
    instrument_id: str
    question_count: int | None = None
    profile_markdown: str = ""
    instruction_markdown: str = ""
    context_markdown: str = ""
    questionnaire_markdown: str = ""
    output_schema_markdown: str = ""
    questionnaire: Dict[str, Any] | None = None
    survey_kind: str = "contributing"
    meta_type: str = "survey"
    domain: str = ""
    difficulty: str = "easy"
    task_kind: str = "task"
    tags: tuple[str, ...] = ()

    def to_summary_dict(self) -> Dict[str, Any]:
        """Return list-endpoint payload without heavy markdown or questionnaire bodies."""
        payload: Dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "taskPath": self.task_path,
            "instrumentId": self.instrument_id,
            "surveyKind": self.survey_kind,
            "metaType": self.meta_type,
            "domain": self.domain,
            "difficulty": self.difficulty,
            "taskKind": self.task_kind,
            "tags": list(self.tags),
        }
        if self.question_count is not None:
            payload["questionCount"] = self.question_count
        return payload

    def to_dict(self) -> Dict[str, Any]:
        return {
            **self.to_summary_dict(),
            "profileMarkdown": self.profile_markdown or None,
            "instructionMarkdown": self.instruction_markdown or None,
            "contextMarkdown": self.context_markdown or None,
            "questionnaireMarkdown": self.questionnaire_markdown or None,
            "outputSchemaMarkdown": self.output_schema_markdown or None,
            "questionnaire": self.questionnaire,
        }
