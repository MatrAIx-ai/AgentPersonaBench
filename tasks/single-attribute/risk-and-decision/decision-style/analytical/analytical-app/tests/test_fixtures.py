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


HELD = [
    {"questionId": "activation", "optionId": "a68"},
    {"questionId": "pricing", "optionId": "p31"},
    {"questionId": "reminders", "optionId": "r14"},
]
VIOLATED = [
    {"questionId": "activation", "optionId": "a17"},
    {"questionId": "pricing", "optionId": "p31"},
    {"questionId": "reminders", "optionId": "r14"},
]

tampered_events = artifact(HELD)
tampered_events["events"][0]["optionId"] = "a17"

changed_answer = artifact(HELD)
changed_answer["events"].insert(
    0, {"event": "select", "questionId": "activation", "optionId": "a17"}
)

CASES = {
    "held": (artifact(HELD), 0, "HELD"),
    "changed_answer": (changed_answer, 0, "HELD"),
    "violated": (artifact(VIOLATED), 1, "VIOLATED"),
    "incomplete": (artifact(HELD[:2]), 1, "VIOLATED"),
    "not_submitted": (artifact(HELD, submitted=False), 1, "VIOLATED"),
    "unexpected_field": (
        artifact([{**HELD[0], "analytical": False}, *HELD[1:]]),
        1,
        "VIOLATED",
    ),
    "unknown": (artifact([{**HELD[0], "optionId": "bogus"}, *HELD[1:]]), 1, "VIOLATED"),
    "tampered_events": (tampered_events, 1, "VIOLATED"),
}

for name, (value, expected_code, expected_verdict) in CASES.items():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "review.json").write_text(json.dumps(value), encoding="utf-8")
        env = {**os.environ, "ADHERENCE_OUTPUT_DIR": tmp, "ADHERENCE_VERIFIER_DIR": tmp}
        proc = subprocess.run(
            [sys.executable, str(HERE / "verifier.py")],
            env=env,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == expected_code, (name, proc.stdout, proc.stderr)
        result = json.loads((root / "structured_output.json").read_text(encoding="utf-8"))
        assert result["verdict"] == expected_verdict, (name, result)

print("analytical app fixtures passed")
