"""Render survey markdown assets from a normalized task-backed questionnaire."""

from __future__ import annotations

from backend.service.survey_types import SurveyInstrument, SurveyQuestion, SurveyTaskContent


def _render_question(question: SurveyQuestion, instrument: SurveyInstrument) -> list[str]:
    ask_rationale = question.resolves_ask_rationale(instrument)
    ask_confidence = question.resolves_ask_confidence(instrument)
    lines = ["## {}".format(question.id), ""]
    if question.prompt:
        lines.append("Prompt: {}".format(question.prompt))
        lines.append("")
    if question.construct:
        lines.append("- Construct: `{}`".format(question.construct))
    lines.append("- Type: `{}`".format(question.type))
    lines.append("- Required: `{}`".format("true" if question.required else "false"))
    if ask_rationale:
        lines.append("- Ask rationale: `true`")
    if ask_confidence:
        lines.append("- Ask confidence: `true`")
    if question.type == "likert":
        lines.append("- Scale: `{}`-`{}`".format(question.min_value, question.max_value))
    lines.append("")
    if question.type == "likert":
        lines.append(
            "Rate with an integer between **{}** and **{}**.".format(
                question.min_value,
                question.max_value,
            )
        )
        lines.append("")
    elif question.type == "single_choice":
        lines.append("| choice_id | label |")
        lines.append("|-----------|-------|")
        for option in question.option_details:
            lines.append("| `{}` | {} |".format(option.id, option.label or option.id))
        if not question.option_details:
            for option in question.options:
                lines.append("| `{}` | {} |".format(option, option))
    elif question.type == "multi_choice":
        lines.append("| choice_id | label |")
        lines.append("|-----------|-------|")
        for option in question.option_details:
            lines.append("| `{}` | {} |".format(option.id, option.label or option.id))
        if not question.option_details:
            for option in question.options:
                lines.append("| `{}` | {} |".format(option, option))
    elif question.type == "free_text":
        lines.append("Respond in a short free-text answer.")
    if ask_rationale:
        lines.append("")
        lines.append("Include a concise `rationale` specific to this answer.")
    if ask_confidence:
        lines.append("")
        lines.append("Include a `confidence` score between 0 and 1 for this answer.")
    lines.append("")
    return lines


def render_survey_task_instruction_markdown(instrument: SurveyInstrument) -> str:
    title = (instrument.title or "this survey").strip()
    blurb = (instrument.description or "").strip()
    goal = blurb or "Answer every required question using the task context and questionnaire."
    return "\n".join(
        [
            "Answer **{}**.".format(title),
            "",
            goal,
            "",
            "## How to answer",
            "",
            "- Read the task context before answering.",
            "- Answer every required question.",
            "- Use the exact choice ids for choice questions.",
            "- For likert questions, use an integer in the declared range.",
            "- Answer with the selected value only unless a question explicitly",
            "  asks for `askRationale` / `askConfidence`.",
            "",
            "The platform records your answers; do not invent submission file paths.",
        ]
    ).strip() + "\n"


def render_survey_context_markdown(instrument: SurveyInstrument) -> str:
    return (
        (instrument.description or "Complete each required question using the provided survey materials.").strip()
        + "\n"
    )


def render_survey_questionnaire_markdown(instrument: SurveyInstrument) -> str:
    lines = [
        "# {}".format(instrument.title),
        "",
        "Use exact `questionId` and valid choice ids.",
        "",
    ]
    if instrument.ask_rationale or instrument.ask_confidence:
        lines.extend(
            [
                "Instrument defaults: `askRationale={}` · `askConfidence={}`.".format(
                    "true" if instrument.ask_rationale else "false",
                    "true" if instrument.ask_confidence else "false",
                ),
                "",
            ]
        )
    for question in instrument.questions:
        lines.extend(_render_question(question, instrument))
    return "\n".join(lines).strip() + "\n"


def render_survey_output_schema_markdown(instrument: SurveyInstrument) -> str:
    """Derived answer envelope for UI/debrief — not a contributor-authored asset."""
    example = instrument.questions[0] if instrument.questions else None
    example_question_id = example.id if example else "q1"
    ask_rationale = (
        example.resolves_ask_rationale(instrument) if example else instrument.ask_rationale
    )
    ask_confidence = (
        example.resolves_ask_confidence(instrument) if example else instrument.ask_confidence
    )
    answer_fields = [
        '      "questionId": "%s",' % example_question_id,
        '      "value": "<answer value>"',
    ]
    if ask_rationale:
        answer_fields[-1] += ","
        answer_fields.append('      "rationale": "Brief answer-specific reason."')
    if ask_confidence:
        answer_fields[-1] += ","
        answer_fields.append('      "confidence": 0.85')
    lines = [
        "Platform-derived answer envelope (from `questionnaire.yaml`).",
        "",
        "```json",
        "{",
        '  "instrument": {"id": "%s", "title": "%s"},'
        % (instrument.id, instrument.title.replace('"', '\\"')),
        '  "answers": [',
        "    {",
        *answer_fields,
        "    }",
        "  ]",
        "}",
        "```",
        "",
        "Use exact `questionId` values from the questionnaire.",
        "For choice questions, `value` must be the exact choice id (or list of ids for multi-select).",
    ]
    if ask_rationale or ask_confidence:
        lines.append(
            "Include `rationale` / `confidence` only when the questionnaire asks for them."
        )
    else:
        lines.append(
            "Default surveys emit `questionId` + `value` only (choice / likert / bool)."
        )
    return "\n".join(lines).strip() + "\n"


def render_survey_instruction_markdown(instrument: SurveyInstrument) -> str:
    """Backward-compatible combined markdown from a normalized questionnaire."""
    content = SurveyTaskContent(
        title=instrument.title,
        instruction_markdown=render_survey_task_instruction_markdown(instrument),
        context_markdown=render_survey_context_markdown(instrument),
        questionnaire_markdown=render_survey_questionnaire_markdown(instrument),
        output_schema_markdown=render_survey_output_schema_markdown(instrument),
        instrument=instrument,
    )
    return content.combined_markdown().strip() + "\n"
