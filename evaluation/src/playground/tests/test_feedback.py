from __future__ import annotations

from playground.feedback import questionnaire_from_feedback


def test_questionnaire_from_feedback_normalizes_artifact_payload():
    questionnaire = questionnaire_from_feedback(
        {
            "needConstraintSatisfaction": "false",
            "personalPreferenceSatisfaction": True,
            "overallExperienceRating": 2,
            "reason": "It did not adapt after I clarified my constraints.",
            "askedUsefulClarificationQuestions": True,
            "clarifyingNotes": "The questions were fine, but the follow-through failed.",
            "customFacet": "preserve me",
        }
    )

    assert questionnaire.to_dict()["constraintSatisfaction"] == 1
    assert questionnaire.to_dict()["preferenceSatisfaction"] == 5
    assert questionnaire.artifact_dict()["needConstraintSatisfaction"] == "no"
    assert questionnaire.artifact_dict()["personalPreferenceSatisfaction"] == "yes"
    assert questionnaire.artifact_dict()["customFacet"] == "preserve me"


def test_questionnaire_from_feedback_does_not_invent_missing_default_fields():
    questionnaire = questionnaire_from_feedback(
        {
            "needConstraintSatisfaction": "yes",
            "overallExperienceRating": 3,
            "reason": "HCP and ANSS were unusable.",
            "hcpDelistingHandled": "no",
        }
    )
    payload = questionnaire.to_dict()
    assert payload["overallRating"] == 3
    assert payload["constraintSatisfaction"] == 5
    # Preference was not authored — must not become yes→5.
    assert payload["preferenceSatisfaction"] == 0
    assert payload["preferenceRationale"] == ""
    assert payload["constraintRationale"] == ""
    assert payload["ratingReason"] == "HCP and ANSS were unusable."
    assert payload["hcpDelistingHandled"] == "no"
    assert payload["askedUsefulClarifyingQuestions"] is False
