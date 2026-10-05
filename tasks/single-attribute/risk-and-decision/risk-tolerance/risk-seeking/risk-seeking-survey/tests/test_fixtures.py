#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent

questionnaire = yaml.safe_load(
    (TASK_DIR / "input" / "questionnaire.yaml").read_text(encoding="utf-8")
)
assert isinstance(questionnaire, dict) and set(questionnaire) == {"questions"}
questions = questionnaire["questions"]
assert isinstance(questions, list) and len(questions) == 36

questionnaire_order: dict[str, list[str]] = {}
for question in questions:
    assert isinstance(question, dict) and set(question) == {"id", "prompt", "type", "options"}
    assert question["type"] == "single_choice"
    assert isinstance(question["id"], str) and question["id"] not in questionnaire_order
    assert isinstance(question["prompt"], str) and question["prompt"].strip()
    assert isinstance(question["options"], list) and len(question["options"]) == 4
    option_ids = []
    for option in question["options"]:
        assert isinstance(option, dict) and set(option) == {"id", "text"}
        assert isinstance(option["id"], str) and isinstance(option["text"], str)
        assert option["id"] not in option_ids and option["text"].strip()
        option_ids.append(option["id"])
    questionnaire_order[question["id"]] = option_ids

answer_key = json.loads((HERE / "answer_key.json").read_text(encoding="utf-8"))
assert set(answer_key) == {"threshold", "facet_threshold", "questions"}
specs = answer_key["questions"]
assert set(specs) == set(questionnaire_order)
assert Counter(spec["facet"] for spec in specs.values()) == {
    "chance_and_variance": 6,
    "career_and_income": 6,
    "commitment_and_launch": 6,
    "ambiguity_and_newness": 6,
    "timing_and_logistics": 6,
    "competition_and_social_stakes": 6,
}
for question_id, option_ids in questionnaire_order.items():
    assert set(specs[question_id]) == {"facet", "scores"}
    assert set(specs[question_id]["scores"]) == set(option_ids)
    assert set(specs[question_id]["scores"].values()) == {0, 1, 2, 3}

for score in range(4):
    positions = [
        questionnaire_order[question_id].index(
            next(
                option_id
                for option_id, option_score in spec["scores"].items()
                if option_score == score
            )
        )
        for question_id, spec in specs.items()
    ]
    assert Counter(positions) == {0: 9, 1: 9, 2: 9, 3: 9}


def option_for_score(question_id: str, score: int) -> str:
    return next(
        option_id
        for option_id, option_score in specs[question_id]["scores"].items()
        if option_score == score
    )


def artifact(levels: dict[str, int] | None = None, *, default: int = 0) -> dict[str, object]:
    chosen = levels or {}
    return {
        "answers": [
            {
                "questionId": question_id,
                "selectedOptionId": option_for_score(
                    question_id, chosen.get(question_id, default)
                ),
            }
            for question_id in specs
        ]
    }


all_high = artifact(default=3)
at_threshold = artifact(default=2)
below_threshold = artifact({next(iter(specs)): 1}, default=2)
facet_failure_levels = {question_id: 2 for question_id in specs}
for question_id, spec in specs.items():
    if spec["facet"] == "chance_and_variance":
        facet_failure_levels[question_id] = 1
    elif spec["facet"] == "career_and_income":
        facet_failure_levels[question_id] = 3
facet_failure = artifact(facet_failure_levels)
incomplete = artifact(default=3)
incomplete["answers"] = incomplete["answers"][:-1]
duplicate = artifact(default=3)
duplicate["answers"][1] = dict(duplicate["answers"][0])
cross_question = artifact(default=3)
cross_question["answers"][0]["selectedOptionId"] = cross_question["answers"][1][
    "selectedOptionId"
]
wrong_question_type = artifact(default=3)
wrong_question_type["answers"][0]["questionId"] = 7
wrong_option_type = artifact(default=3)
wrong_option_type["answers"][0]["selectedOptionId"] = {"id": "forged"}
extra_field = artifact(default=3)
extra_field["answers"][0]["score"] = 3

CASES = {
    "held_maximum": (all_high, 0, "HELD"),
    "held_threshold": (at_threshold, 0, "HELD"),
    "violated_below_threshold": (below_threshold, 1, "VIOLATED"),
    "violated_facet_floor": (facet_failure, 1, "VIOLATED"),
    "violated_minimum": (artifact(), 1, "VIOLATED"),
    "incomplete": (incomplete, 1, "VIOLATED"),
    "duplicate": (duplicate, 1, "VIOLATED"),
    "unknown_question": (
        {"answers": [{"questionId": "bogus", "selectedOptionId": "bd89"}]},
        1,
        "VIOLATED",
    ),
    "cross_question": (cross_question, 1, "VIOLATED"),
    "top_level_list": ([], 1, "VIOLATED"),
    "answers_wrong_type": ({"answers": {}}, 1, "VIOLATED"),
    "question_id_wrong_type": (wrong_question_type, 1, "VIOLATED"),
    "option_id_wrong_type": (wrong_option_type, 1, "VIOLATED"),
    "forged_extra_field": (extra_field, 1, "VIOLATED"),
}

for name, (value, expected_code, expected_verdict) in CASES.items():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "survey_result.json").write_text(json.dumps(value), encoding="utf-8")
        env = {
            **os.environ,
            "ADHERENCE_OUTPUT_DIR": tmp,
            "ADHERENCE_VERIFIER_DIR": tmp,
        }
        proc = subprocess.run(
            ["bash", str(HERE / "test.sh")],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == expected_code, (name, proc.stdout, proc.stderr)
        result = json.loads((root / "structured_output.json").read_text(encoding="utf-8"))
        assert result["verdict"] == expected_verdict, (name, result)
        assert (root / "reward.txt").is_file(), name

print("risk-seeking survey fixtures passed")
