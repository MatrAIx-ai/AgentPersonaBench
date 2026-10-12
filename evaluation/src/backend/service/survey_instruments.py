"""Compatibility shim for the old survey instrument catalog module."""

from .survey_questionnaire_catalog import (
    DEFAULT_SURVEY_QUESTIONNAIRE_ID,
    get_survey_questionnaire,
    list_survey_questionnaires,
)

DEFAULT_SURVEY_INSTRUMENT_ID = DEFAULT_SURVEY_QUESTIONNAIRE_ID
get_survey_instrument = get_survey_questionnaire
list_survey_instruments = list_survey_questionnaires

__all__ = [
    "DEFAULT_SURVEY_INSTRUMENT_ID",
    "get_survey_instrument",
    "list_survey_instruments",
]
