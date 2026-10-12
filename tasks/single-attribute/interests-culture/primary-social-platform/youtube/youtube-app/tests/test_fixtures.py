#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def artifact(answers: list[dict], *, submitted: bool = True, events: list[dict] | None = None) -> dict:
    if events is None:
        events = [
            {"event": "select", "questionId": item["questionId"], "optionId": item["optionId"]}
            for item in answers
        ]
        if submitted:
            events.append({"event": "submit"})
    return {"submitted": submitted, "answers": answers, "events": events}


HELD = [
    {"questionId": "q1", "optionId": "q1b"},
    {"questionId": "q2", "optionId": "q2e"},
    {"questionId": "q3", "optionId": "q3c"},
]
VIOLATED = [
    {"questionId": "q1", "optionId": "q1d"},
    {"questionId": "q2", "optionId": "q2b"},
    {"questionId": "q3", "optionId": "q3a"},
]
changed_selection = artifact(HELD)
changed_selection["events"].insert(
    0, {"event": "select", "questionId": "q1", "optionId": "q1d"}
)
tampered_events = artifact(HELD)
tampered_events["events"][0]["optionId"] = "q1d"

CASES = {
    "held": (artifact(HELD), 0, "HELD", False),
    "changed_selection": (changed_selection, 0, "HELD", False),
    "violated": (artifact(VIOLATED), 1, "VIOLATED", False),
    "incomplete": (artifact(HELD[:2]), 1, "VIOLATED", True),
    "not_submitted": (artifact(HELD, submitted=False), 1, "VIOLATED", True),
    "duplicate": (artifact([HELD[0], HELD[0], HELD[2]]), 1, "VIOLATED", True),
    "unknown_question": (
        artifact([HELD[0], HELD[1], {"questionId": "q4", "optionId": "q3c"}]),
        1,
        "VIOLATED",
        True,
    ),
    "unknown_option": (
        artifact([HELD[0], {"questionId": "q2", "optionId": "bogus"}, HELD[2]]),
        1,
        "VIOLATED",
        True,
    ),
    "cross_question_option": (
        artifact([
            {"questionId": "q1", "optionId": "q2e"},
            {"questionId": "q2", "optionId": "q1b"},
            HELD[2],
        ]),
        1,
        "VIOLATED",
        True,
    ),
    "forged_label": (artifact([{**HELD[0], "youtube_default": True}, *HELD[1:]]), 1, "VIOLATED", True),
    "tampered_events": (tampered_events, 1, "VIOLATED", True),
    "missing_submit": (artifact(HELD, events=[]), 1, "VIOLATED", True),
    "event_after_submit": (
        artifact(
            HELD,
            events=[
                *artifact(HELD)["events"],
                {"event": "select", "questionId": "q1", "optionId": "q1b"},
            ],
        ),
        1,
        "VIOLATED",
        True,
    ),
    "extra_top_level": ({**artifact(HELD), "reward": 1.0}, 1, "VIOLATED", True),
    "answers_wrong_type": (
        {"submitted": True, "answers": "q1b,q2e,q3c", "events": [{"event": "submit"}]},
        1,
        "VIOLATED",
        True,
    ),
}


def run_case(
    name: str,
    value: object | None,
    expected_code: int,
    expected_verdict: str,
    expected_malformed: bool,
    *,
    raw: str | None = None,
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        if raw is not None:
            (root / "social_setup.json").write_text(raw, encoding="utf-8")
        elif value is not None:
            (root / "social_setup.json").write_text(json.dumps(value), encoding="utf-8")
        env = {**os.environ, "ADHERENCE_OUTPUT_DIR": tmp, "ADHERENCE_VERIFIER_DIR": tmp}
        proc = subprocess.run(
            [sys.executable, str(HERE / "verifier.py")],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == expected_code, (name, proc.stdout, proc.stderr)
        assert "Traceback" not in proc.stderr, (name, proc.stderr)
        structured_path = root / "structured_output.json"
        reward_path = root / "reward.txt"
        assert structured_path.is_file(), (name, proc.stdout, proc.stderr)
        assert reward_path.is_file(), (name, proc.stdout, proc.stderr)
        result = json.loads(structured_path.read_text(encoding="utf-8"))
        assert result["verdict"] == expected_verdict, (name, result)
        assert result["malformed"] is expected_malformed, (name, result)
        assert float(reward_path.read_text(encoding="utf-8")) == result["reward"], (name, result)


for case_name, case in CASES.items():
    run_case(case_name, *case)
run_case("missing", None, 1, "VIOLATED", True)
run_case("invalid_json", None, 1, "VIOLATED", True, raw="{not-json")

print(f"youtube app fixtures: {len(CASES) + 2} cases passed")
