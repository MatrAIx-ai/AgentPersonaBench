"""Normalize task-owned self-report artifacts into the shared UI questionnaire."""

from __future__ import annotations

from typing import Any, Dict

from playground.types import Questionnaire
from playground.user_sim.self_report_contract import (
    DEFAULT_CHATBOT_SELF_REPORT_SCHEMA,
    SelfReportField,
    SelfReportSchema,
    coerce_self_report_payload,
    field_keys,
    merge_extra_fields,
)


def _coerce_score(value: Any, default: int) -> int:
    text = str(value or "").strip().lower()
    if text == "yes":
        return 5
    if text == "partially":
        return 3
    if text == "no":
        return 1
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return max(1, min(5, number))


def _coerce_overall(value: Any, default: int = 5) -> int:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return max(1, min(10, number))


def _subset_default_schema(present_keys: set[str]) -> SelfReportSchema | None:
    fields = tuple(
        field
        for field in DEFAULT_CHATBOT_SELF_REPORT_SCHEMA.fields
        if field.key in present_keys
    )
    if not fields:
        return None
    # Mark as required=False so coerce won't invent values for siblings.
    relaxed = tuple(
        SelfReportField(
            key=field.key,
            prompt=field.prompt,
            kind=field.kind,
            required=False,
            minimum=field.minimum,
            maximum=field.maximum,
            choices=field.choices,
            explains=field.explains,
        )
        for field in fields
    )
    return SelfReportSchema(
        artifact_name=DEFAULT_CHATBOT_SELF_REPORT_SCHEMA.artifact_name,
        instructions=DEFAULT_CHATBOT_SELF_REPORT_SCHEMA.instructions,
        fields=relaxed,
    )


def questionnaire_from_feedback(feedback: Dict[str, Any]) -> Questionnaire:
    """Map ``user_feedback.json`` into the legacy scorecard shape.

    Only populate constraint / preference / clarifying slots when those keys
    are actually present in the artifact. Do **not** fill missing default-schema
    enums (that previously turned absent preference into yes→5).
    """
    raw = dict(feedback or {})
    known_default_keys = set(field_keys(DEFAULT_CHATBOT_SELF_REPORT_SCHEMA))
    present_default = {key: raw[key] for key in known_default_keys if key in raw}
    subset = _subset_default_schema(set(present_default))
    normalized_present = (
        coerce_self_report_payload(present_default, subset) if subset is not None else {}
    )
    extra_feedback = merge_extra_fields(raw, exclude=known_default_keys)
    artifact_payload = {**raw, **normalized_present}

    reason = str(normalized_present.get("reason") or raw.get("reason") or "")
    has_need = "needConstraintSatisfaction" in raw
    has_pref = "personalPreferenceSatisfaction" in raw
    has_clarify = "askedUsefulClarificationQuestions" in raw
    clarifying_notes = str(
        normalized_present.get("clarifyingNotes") or raw.get("clarifyingNotes") or ""
    )

    return Questionnaire(
        constraint_satisfaction=(
            _coerce_score(normalized_present.get("needConstraintSatisfaction"), 3)
            if has_need
            else 0
        ),
        constraint_rationale="",
        preference_satisfaction=(
            _coerce_score(normalized_present.get("personalPreferenceSatisfaction"), 3)
            if has_pref
            else 0
        ),
        preference_rationale="",
        overall_rating=_coerce_overall(
            normalized_present.get(
                "overallExperienceRating", raw.get("overallExperienceRating")
            )
        ),
        rating_reason=reason,
        asked_useful_clarifying_questions=(
            bool(normalized_present.get("askedUsefulClarificationQuestions", False))
            if has_clarify
            else False
        ),
        clarifying_notes=clarifying_notes if has_clarify or clarifying_notes else "",
        extra_fields=extra_feedback,
        artifact_payload=artifact_payload,
    )
