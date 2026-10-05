"""Cross-dimension consistency rules for synthetic persona generation."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DEFAULT_CATALOG_PATH = "persona/schema/dimensions.json"

# Standard checked-in / Playground persona fields are defined by
# ``load_dev_dimension_ids()``: core block + all ``cog_*`` + food/diet/cuisine.
#
# Core catalog block (index 1-47): demographics, career, values, interaction
# state, etc. Do not raise CORE_DEV_MAX_INDEX to pull food dims — that would also
# ingest the fam_* / att_* floods that start at index 48+.
CORE_DEV_MAX_INDEX = 47
CORE_DEV_DIMENSION_IDS = (
    "age_bracket",
    "region",
    "gender_identity",
    "urbanicity",
    "socioeconomic_band",
    "primary_language",
    "english_proficiency",
    "multilingualism",
    "register",
    "domain",
    "subject_specialty",
    "domain_characteristics",
    "highest_education",
    "academic_field",
    "institution_tier",
    "research_output",
    "seniority",
    "company_size",
    "role_function",
    "years_experience",
    "linkedin_activity",
    "life_stage",
    "major_life_events",
    "cultural_background",
    "tech_savviness",
    "dominant_trait",
    "risk_tolerance",
    "decision_style",
    "values_priority",
    "political_lean",
    "religiosity",
    "neurotype",
    "emotional_state",
    "intent",
    "query_complexity",
    "expertise_gap",
    "tone_expected",
    "trust_level",
    "safety_sensitivity",
    "time_pressure",
    "prior_context",
    "device_context",
    "modality_pref",
    "accessibility_needs",
    "learning_style",
    "media_diet",
    "economic_motivation",
)
CORE_DEV_DIMENSION_ORDER = {
    dim_id: index for index, dim_id in enumerate(CORE_DEV_DIMENSION_IDS, start=1)
}

# Food / diet / cooking fields that belong in the standard dev set (plus every
# ``cuis_*`` id from the catalog — matched by prefix in ``load_dev_dimension_ids``).
DEV_FOOD_DIMENSION_IDS = frozenset(
    {
        "lstyle_diet_type",
        "fam_nutrition",
        "att_veganism",
        "health_dietary_restriction",
        "habit_meal_prepping",
        "habit_skipping_breakfast",
        "habit_late_night_snacking",
    }
)

# life_stage must be plausible for age_bracket (no counterfactual life arcs).
LIFE_STAGE_BY_AGE: dict[str, list[str]] = {
    "Under 5": ["Student"],
    "5-12": ["Student"],
    "13-17": ["Student"],
    "18-24": ["Student", "Early career"],
    "25-34": ["Early career", "Parent of young kids", "Career change"],
    "35-44": ["Mid-life", "Parent of young kids", "Early career", "Career change"],
    "45-54": ["Mid-life", "Parent of young kids", "Empty nester", "Career change"],
    "55-64": ["Mid-life", "Empty nester", "Career change", "Retirement"],
    "65-74": ["Retirement", "Empty nester"],
    "75-84": ["Retirement", "Empty nester"],
    "85+": ["Retirement", "Empty nester"],
}

SENIORITY_BY_LIFE_STAGE: dict[str, list[str]] = {
    "Student": ["Student / intern"],
    "Early career": ["Student / intern", "Entry", "Mid"],
    "Parent of young kids": ["Entry", "Mid", "Senior", "Manager"],
    "Mid-life": ["Mid", "Senior", "Lead / Principal", "Manager", "Director"],
    "Career change": ["Entry", "Mid", "Senior"],
    "Empty nester": ["Senior", "Lead / Principal", "Manager", "Director", "VP"],
    "Retirement": ["Retired"],
}

EDUCATION_BY_AGE: dict[str, list[str]] = {
    "Under 5": ["No formal"],
    "5-12": ["No formal", "Primary"],
    "13-17": ["No formal", "Primary", "Secondary"],
    "18-24": [
        "Secondary",
        "Vocational / cert",
        "Some college",
        "Associate's",
        "Bachelor's",
    ],
    "25-34": [
        "Secondary",
        "Vocational / cert",
        "Some college",
        "Associate's",
        "Bachelor's",
        "Master's",
    ],
    "35-44": [
        "Vocational / cert",
        "Some college",
        "Associate's",
        "Bachelor's",
        "Master's",
        "Doctorate",
    ],
    "45-54": [
        "Bachelor's",
        "Master's",
        "Doctorate",
        "Vocational / cert",
        "Some college",
        "Associate's",
    ],
    "55-64": [
        "Secondary",
        "Vocational / cert",
        "Some college",
        "Associate's",
        "Bachelor's",
        "Master's",
        "Doctorate",
    ],
    "65-74": [
        "Secondary",
        "Vocational / cert",
        "Some college",
        "Associate's",
        "Bachelor's",
        "Master's",
        "Doctorate",
    ],
    "75-84": [
        "Secondary",
        "Vocational / cert",
        "Some college",
        "Associate's",
        "Bachelor's",
        "Master's",
        "Doctorate",
    ],
    "85+": [
        "Secondary",
        "Vocational / cert",
        "Some college",
        "Associate's",
        "Bachelor's",
        "Master's",
        "Doctorate",
    ],
}

CONSTRAINED_DIMENSIONS = frozenset(
    {
        "age_bracket",
        "life_stage",
        "seniority",
        "years_experience",
        "highest_education",
    }
)


def _canonical_age_bracket(age_bracket: str) -> str:
    return age_bracket.replace("–", "-")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@lru_cache(maxsize=4)
def _load_catalog_rows(catalog_path: str) -> list[dict[str, Any]]:
    path = Path(catalog_path)
    if not path.is_file():
        path = _repo_root() / catalog_path
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for position, row in enumerate(payload.get("dimensions") or []):
        if isinstance(row, dict) and row.get("id"):
            rows.append({**row, "_catalog_order": position})
    return sorted(rows, key=lambda r: (_catalog_order(r), str(r["id"])))


def _catalog_order(row: dict[str, Any]) -> int:
    if row.get("index") is not None:
        return int(row["index"])
    dim_id = str(row["id"])
    if dim_id in CORE_DEV_DIMENSION_ORDER:
        return CORE_DEV_DIMENSION_ORDER[dim_id]
    return CORE_DEV_MAX_INDEX + 1 + int(row.get("_catalog_order") or 99999)


def load_dev_dimension_ids(
    *, catalog_path: str = DEFAULT_CATALOG_PATH
) -> tuple[str, ...]:
    """Standard persona fields for matraix-persona-dev-sample and Playground generation.

    Includes the core block (index ≤ 47), all ``cog_*`` communication dims,
    food/diet/cooking dims (``DEV_FOOD_DIMENSION_IDS``), and every ``cuis_*``.
    """
    ids: list[str] = []
    for row in _load_catalog_rows(catalog_path):
        dim_id = str(row["id"])
        index = _catalog_order(row)
        if (
            index <= CORE_DEV_MAX_INDEX
            or dim_id in CORE_DEV_DIMENSION_ORDER
            or dim_id.startswith("cog_")
            or dim_id in DEV_FOOD_DIMENSION_IDS
            or dim_id.startswith("cuis_")
        ):
            ids.append(dim_id)
    return tuple(ids)


@lru_cache(maxsize=4)
def load_dev_dimension_index_order(
    *, catalog_path: str = DEFAULT_CATALOG_PATH
) -> dict[str, int]:
    dev_ids = set(load_dev_dimension_ids(catalog_path=catalog_path))
    order: dict[str, int] = {}
    for row in _load_catalog_rows(catalog_path):
        dim_id = str(row["id"])
        if dim_id in dev_ids:
            order[dim_id] = _catalog_order(row)
    return order


def allowed_years_experience(*, age_bracket: str, seniority: str) -> list[str]:
    age_bracket = _canonical_age_bracket(age_bracket)
    if seniority == "Retired":
        return ["11-20", "20+"]
    if seniority in ("Student / intern",):
        return ["0-2"]
    if seniority == "Entry":
        return ["0-2", "3-5"]
    if age_bracket in ("Under 5", "5-12", "13-17", "18-24"):
        return ["0-2", "3-5"]
    if age_bracket == "25-34":
        return ["0-2", "3-5", "6-10"]
    if age_bracket in ("35-44", "45-54"):
        return ["3-5", "6-10", "11-20"]
    return ["6-10", "11-20", "20+"]


def allowed_life_stages(age_bracket: str) -> list[str]:
    age_bracket = _canonical_age_bracket(age_bracket)
    return list(LIFE_STAGE_BY_AGE.get(age_bracket, []))


def allowed_age_brackets_for_life_stage(life_stage: str) -> list[str]:
    """Ages that can host *life_stage* (inverse of ``LIFE_STAGE_BY_AGE``)."""
    return [
        age
        for age, stages in LIFE_STAGE_BY_AGE.items()
        if life_stage in stages
    ]


def allowed_seniorities(*, life_stage: str, age_bracket: str) -> list[str]:
    age_bracket = _canonical_age_bracket(age_bracket)
    options = list(SENIORITY_BY_LIFE_STAGE.get(life_stage, []))
    if age_bracket in ("Under 5", "5-12", "13-17", "18-24"):
        return [s for s in options if s in ("Student / intern", "Entry", "Mid")]
    if age_bracket in ("65-74", "75-84", "85+"):
        return [
            s
            for s in options
            if s in ("Retired", "Senior", "Lead / Principal", "Director", "VP")
        ]
    return options


def allowed_education(*, age_bracket: str, life_stage: str) -> list[str]:
    age_bracket = _canonical_age_bracket(age_bracket)
    base = list(EDUCATION_BY_AGE.get(age_bracket, []))
    if life_stage == "Student" and age_bracket in (
        "Under 5",
        "5-12",
        "13-17",
        "18-24",
    ):
        return [
            e
            for e in base
            if e
            in (
                "No formal",
                "Primary",
                "Secondary",
                "Vocational / cert",
                "Some college",
                "Associate's",
                "Bachelor's",
            )
        ]
    return base


def validate_dimensions(dimensions: dict[str, Any]) -> list[str]:
    """Return human-readable counterfactual violations (empty if consistent)."""
    errors: list[str] = []
    age = dimensions.get("age_bracket")
    life = dimensions.get("life_stage")
    seniority = dimensions.get("seniority")
    years = dimensions.get("years_experience")
    education = dimensions.get("highest_education")

    if isinstance(age, str) and isinstance(life, str):
        allowed = allowed_life_stages(age)
        if life not in allowed:
            errors.append(f"life_stage={life!r} incompatible with age_bracket={age!r}")

    if isinstance(life, str) and isinstance(seniority, str):
        allowed = allowed_seniorities(life_stage=life, age_bracket=str(age or ""))
        if seniority not in allowed:
            errors.append(
                f"seniority={seniority!r} incompatible with life_stage={life!r} "
                f"and age_bracket={age!r}"
            )

    if isinstance(age, str) and isinstance(seniority, str) and isinstance(years, str):
        allowed = allowed_years_experience(age_bracket=age, seniority=seniority)
        if years not in allowed:
            errors.append(
                f"years_experience={years!r} incompatible with age_bracket={age!r} "
                f"and seniority={seniority!r}"
            )

    if isinstance(age, str) and isinstance(life, str) and isinstance(education, str):
        allowed = allowed_education(age_bracket=age, life_stage=life)
        if education not in allowed:
            errors.append(
                f"highest_education={education!r} incompatible with age_bracket={age!r} "
                f"and life_stage={life!r}"
            )

    return errors
