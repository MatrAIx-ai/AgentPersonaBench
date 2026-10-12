#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def artifact(answers: list[dict], *, submitted: bool = True) -> dict:
    events = [
        {"event": "select", "questionId": item["questionId"], "optionId": item["optionId"]}
        for item in answers
    ]
    if submitted:
        events.append({"event": "submit"})
    return {"submitted": submitted, "answers": answers, "events": events}


GOOD = [
    {"questionId": "activation", "optionId": "a68"},
    {"questionId": "pricing", "optionId": "p31"},
    {"questionId": "reminders", "optionId": "r14"},
]
BAD = [
    {"questionId": "activation", "optionId": "a17"},
    {"questionId": "pricing", "optionId": "p31"},
    {"questionId": "reminders", "optionId": "r14"},
]

CHANGED_ANSWER = artifact(GOOD)
CHANGED_ANSWER["events"].insert(
    0, {"event": "select", "questionId": "activation", "optionId": "a17"}
)

CASES = {
    "held": (artifact(GOOD), 0, "HELD"),
    "changed_answer": (CHANGED_ANSWER, 0, "HELD"),
    "violated": (artifact(BAD), 1, "VIOLATED"),
    "incomplete": (artifact(GOOD[:2]), 1, "VIOLATED"),
    "not_submitted": (artifact(GOOD, submitted=False), 1, "VIOLATED"),
    "unexpected_field": (
        artifact([{**GOOD[0], "analytical": False}, *GOOD[1:]]),
        1,
        "VIOLATED",
    ),
    "unknown": (artifact([{**GOOD[0], "optionId": "bogus"}, *GOOD[1:]]), 1, "VIOLATED"),
}

for name, (value, expected_code, expected_verdict) in CASES.items():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "anchor").mkdir()
        (root / "anchor" / "review.json").write_text(json.dumps(value), encoding="utf-8")
        env = {**os.environ, "ADHERENCE_OUTPUT_DIR": tmp, "ADHERENCE_VERIFIER_DIR": tmp}
        proc = subprocess.run(
            [sys.executable, str(HERE / "verifier.py")], env=env, capture_output=True, text=True
        )
        assert proc.returncode == expected_code, (name, proc.stdout, proc.stderr)
        result = json.loads((root / "structured_output.json").read_text(encoding="utf-8"))
        assert result["verdict"] == expected_verdict, (name, result)

print("analytical web fixtures passed")
