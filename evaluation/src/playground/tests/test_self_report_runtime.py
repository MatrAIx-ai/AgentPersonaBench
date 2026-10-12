from __future__ import annotations

import json

from playground.self_report_runtime import (
    complete_self_report_payload,
    write_self_report_artifact,
)
from playground.user_sim.self_report_contract import (
    DEFAULT_CHATBOT_SELF_REPORT_SCHEMA,
    SelfReportField,
    SelfReportSchema,
)


def test_complete_self_report_payload_normalizes_and_writes_artifact(tmp_path):
    schema = SelfReportSchema(
        fields=(
            SelfReportField(
                key="satisfaction",
                prompt="How satisfied were you?",
                kind="integer",
                minimum=1,
                maximum=5,
            ),
            SelfReportField(
                key="feltUnderstood",
                prompt="Did you feel understood?",
                kind="boolean",
                required=False,
            ),
        )
    )

    payload = complete_self_report_payload(
        '{"satisfaction": 9, "feltUnderstood": "yes"}',
        system_prompt="system",
        user_prompt="user",
        schema=schema,
    )

    assert payload == {"satisfaction": 5, "feltUnderstood": True}

    output_path = tmp_path / "nested" / "user_feedback.json"
    write_self_report_artifact(payload, output_path=output_path)

    assert json.loads(output_path.read_text(encoding="utf-8")) == payload


def test_complete_self_report_payload_maps_boolean_like_values_for_yes_no_enums():
    payload = complete_self_report_payload(
        json.dumps(
            {
                "needConstraintSatisfaction": "false",
                "personalPreferenceSatisfaction": True,
                "overallExperienceRating": 2,
                "reason": "It did not adapt.",
                "askedUsefulClarificationQuestions": True,
                "clarifyingNotes": "It asked, but did not use the answers.",
            }
        ),
        system_prompt="system",
        user_prompt="user",
        schema=DEFAULT_CHATBOT_SELF_REPORT_SCHEMA,
    )

    assert payload["needConstraintSatisfaction"] == "no"
    assert payload["personalPreferenceSatisfaction"] == "yes"
