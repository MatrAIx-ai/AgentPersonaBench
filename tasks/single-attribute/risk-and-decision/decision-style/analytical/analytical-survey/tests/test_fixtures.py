#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def artifact(*pairs: tuple[str, str]) -> dict:
    return {"answers": [{"questionId": qid, "selectedOptionId": oid} for qid, oid in pairs]}


CASES = {
    "held_three": (artifact(("activation", "a68"), ("pricing", "p31"), ("reminders", "r63")), 0, "HELD"),
    "held_threshold": (artifact(("activation", "a68"), ("pricing", "p31"), ("reminders", "r14")), 0, "HELD"),
    "violated": (artifact(("activation", "a17"), ("pricing", "p31"), ("reminders", "r14")), 1, "VIOLATED"),
    "incomplete": (artifact(("activation", "a68"), ("pricing", "p31")), 1, "VIOLATED"),
    "duplicate": (artifact(("activation", "a68"), ("activation", "a17"), ("reminders", "r63")), 1, "VIOLATED"),
    "unknown": (artifact(("activation", "bogus"), ("pricing", "p31"), ("reminders", "r63")), 1, "VIOLATED"),
    "cross_question_ids": (
        artifact(("activation", "p31"), ("pricing", "a68"), ("reminders", "r14")),
        1,
        "VIOLATED",
    ),
}

for name, (value, expected_code, expected_verdict) in CASES.items():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "survey_result.json").write_text(json.dumps(value), encoding="utf-8")
        env = {**os.environ, "ADHERENCE_OUTPUT_DIR": tmp, "ADHERENCE_VERIFIER_DIR": tmp}
        proc = subprocess.run(
            [sys.executable, str(HERE / "verifier.py")], env=env, capture_output=True, text=True
        )
        assert proc.returncode == expected_code, (name, proc.stdout, proc.stderr)
        result = json.loads((root / "structured_output.json").read_text(encoding="utf-8"))
        assert result["verdict"] == expected_verdict, (name, result)

print("analytical survey fixtures passed")

