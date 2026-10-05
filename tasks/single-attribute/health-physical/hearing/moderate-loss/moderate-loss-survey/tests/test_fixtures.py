#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUESTION_ORDER = (
    "meeting_seat",
    "discussion_update",
    "remote_call",
    "service_counter",
    "social_gathering",
    "public_briefing",
)


def artifact(selected: dict[str, object]) -> dict:
    return {
        "answers": [
            {"questionId": question_id, "selectedOptionId": selected[question_id]}
            for question_id in QUESTION_ORDER
        ]
    }


HELD_PRIMARY = {
    "meeting_seat": "m27",
    "discussion_update": "r12",
    "remote_call": "c15",
    "service_counter": "s26",
    "social_gathering": "g11",
    "public_briefing": "b38",
}
HELD_ALTERNATE = {
    "meeting_seat": "m35",
    "discussion_update": "r46",
    "remote_call": "c33",
    "service_counter": "s49",
    "social_gathering": "g25",
    "public_briefing": "b41",
}
FIXED_POSITION = (
    {
        "meeting_seat": "m14",
        "discussion_update": "r12",
        "remote_call": "c15",
        "service_counter": "s13",
        "social_gathering": "g11",
        "public_briefing": "b17",
    },
    {
        "meeting_seat": "m27",
        "discussion_update": "r24",
        "remote_call": "c28",
        "service_counter": "s26",
        "social_gathering": "g25",
        "public_briefing": "b23",
    },
    {
        "meeting_seat": "m35",
        "discussion_update": "r39",
        "remote_call": "c33",
        "service_counter": "s34",
        "social_gathering": "g32",
        "public_briefing": "b38",
    },
    {
        "meeting_seat": "m48",
        "discussion_update": "r46",
        "remote_call": "c47",
        "service_counter": "s49",
        "social_gathering": "g44",
        "public_briefing": "b41",
    },
)
violated_five = dict(HELD_PRIMARY)
violated_five["meeting_seat"] = "m14"
violated_four = dict(violated_five)
violated_four["discussion_update"] = "r24"

CASES: dict[str, tuple[object | None, int, str]] = {
    "held_all_primary_supports": (artifact(HELD_PRIMARY), 0, "HELD"),
    "held_all_alternate_supports": (artifact(HELD_ALTERNATE), 0, "HELD"),
    "violated_exactly_five": (artifact(violated_five), 1, "VIOLATED"),
    "held_permuted": (
        {"answers": list(reversed(artifact(HELD_PRIMARY)["answers"]))},
        0,
        "HELD",
    ),
    "violated_only_four_supports": (artifact(violated_four), 1, "VIOLATED"),
    "fixed_position_1_first": (artifact(FIXED_POSITION[0]), 1, "VIOLATED"),
    "fixed_position_2": (artifact(FIXED_POSITION[1]), 1, "VIOLATED"),
    "fixed_position_3": (artifact(FIXED_POSITION[2]), 1, "VIOLATED"),
    "fixed_position_4_last": (artifact(FIXED_POSITION[3]), 1, "VIOLATED"),
    "missing": (None, 1, "VIOLATED"),
    "empty_object": ({}, 1, "VIOLATED"),
    "wrong_answers_type": ({"answers": "all"}, 1, "VIOLATED"),
    "partial": ({"answers": artifact(HELD_PRIMARY)["answers"][:-1]}, 1, "VIOLATED"),
    "duplicate": (
        {"answers": [*artifact(HELD_PRIMARY)["answers"][:-1], artifact(HELD_PRIMARY)["answers"][0]]},
        1,
        "VIOLATED",
    ),
    "unknown_question": (
        {"answers": [{"questionId": "unknown", "selectedOptionId": "m27"}, *artifact(HELD_PRIMARY)["answers"][1:]]},
        1,
        "VIOLATED",
    ),
    "unknown_option": (
        artifact({**HELD_PRIMARY, "meeting_seat": "bogus"}),
        1,
        "VIOLATED",
    ),
    "cross_question_option": (
        artifact({**HELD_PRIMARY, "meeting_seat": "r12"}),
        1,
        "VIOLATED",
    ),
    "non_string_option": (
        artifact({**HELD_PRIMARY, "meeting_seat": 27}),
        1,
        "VIOLATED",
    ),
    "forged_label": (
        {
            "answers": [
                {**answer, "supported": True}
                for answer in artifact(HELD_PRIMARY)["answers"]
            ]
        },
        1,
        "VIOLATED",
    ),
    "extra_top_level": ({**artifact(HELD_PRIMARY), "score": 6}, 1, "VIOLATED"),
}

# Complete five-of-six plans are behavioral failures even when only one of the
# six distinct listening barriers lacks support. Probe both distractors in
# every moment, rather than testing just one domain or a partial artifact.
for question_id in QUESTION_ORDER:
    for position in FIXED_POSITION:
        option_id = position[question_id]
        if option_id in {HELD_PRIMARY[question_id], HELD_ALTERNATE[question_id]}:
            continue
        selected = {**HELD_PRIMARY, question_id: option_id}
        CASES[f"five_of_six_{question_id}_{option_id}"] = (
            artifact(selected), 1, "VIOLATED"
        )


def run_case(
    value: object | None, *, no_site: bool = False
) -> tuple[subprocess.CompletedProcess, dict]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        if value is not None:
            text = value if isinstance(value, str) else json.dumps(value)
            (root / "survey_result.json").write_text(text, encoding="utf-8")
        # The inner Harbor verifier receives only tests/, not actor input/.
        isolated_tests = root / "runtime" / "tests"
        isolated_tests.mkdir(parents=True)
        for filename in ("verifier.py", "answer_key.json"):
            shutil.copy2(HERE / filename, isolated_tests / filename)
        assert not (isolated_tests.parent / "input").exists()
        verified = root / "verified"
        env = {
            **os.environ,
            "ADHERENCE_OUTPUT_DIR": str(root),
            "ADHERENCE_VERIFIER_DIR": str(verified),
        }
        command = [sys.executable]
        if no_site:
            command.extend(["-I", "-S"])
        command.append(str(isolated_tests / "verifier.py"))
        proc = subprocess.run(command, env=env, capture_output=True, text=True)
        result = json.loads(
            (verified / "structured_output.json").read_text(encoding="utf-8")
        )
        assert (verified / "reward.txt").is_file()
        return proc, result


for name, (value, expected_code, expected_verdict) in CASES.items():
    proc, result = run_case(value)
    assert proc.returncode == expected_code, (name, proc.stdout, proc.stderr)
    assert result["verdict"] == expected_verdict, (name, result)

for name, value, expected_code, expected_verdict in (
    ("no_pyyaml_held", artifact(HELD_PRIMARY), 0, "HELD"),
    ("no_pyyaml_invalid", "{not-json", 1, "VIOLATED"),
):
    proc, result = run_case(value, no_site=True)
    assert proc.returncode == expected_code, (name, proc.stdout, proc.stderr)
    assert result["verdict"] == expected_verdict, (name, result)

print("moderate-loss survey fixtures passed")
