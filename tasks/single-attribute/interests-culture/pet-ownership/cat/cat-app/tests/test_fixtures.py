#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
QIDS = ["q1", "q2", "q3"]
OPTIONS = {
    "q1": ["q1a", "q1b", "q1c", "q1d"],
    "q2": ["q2a", "q2b", "q2c", "q2d"],
    "q3": ["q3a", "q3b", "q3c", "q3d"],
}
HELD = [("q1", "q1d"), ("q2", "q2c"), ("q3", "q3b")]
VIOLATED = [("q1", "q1a"), ("q2", "q2a"), ("q3", "q3a")]
WITH_EVENTS = True
ARTIFACT_REL = "selection.json"


def artifact(
    pairs: list[tuple[str, str]],
    *,
    submitted: bool = True,
    events: list[dict] | None = None,
) -> dict:
    if WITH_EVENTS:
        answers = [{"questionId": qid, "optionId": oid} for qid, oid in pairs]
        if events is None:
            events = [
                {"event": "select", "questionId": qid, "optionId": oid}
                for qid, oid in pairs
            ]
            if submitted:
                events.append({"event": "submit"})
        return {"submitted": submitted, "answers": answers, "events": events}
    return {
        "answers": [{"questionId": qid, "selectedOptionId": oid} for qid, oid in pairs]
    }


def run_case(
    name: str,
    value: object | None,
    code: int,
    verdict: str,
    malformed: bool,
    *,
    raw: str | None = None,
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        path = root / ARTIFACT_REL
        path.parent.mkdir(parents=True, exist_ok=True)
        if raw is not None:
            path.write_text(raw, encoding="utf-8")
        elif value is not None:
            path.write_text(json.dumps(value), encoding="utf-8")
        env = {**os.environ, "ADHERENCE_OUTPUT_DIR": tmp, "ADHERENCE_VERIFIER_DIR": tmp}
        proc = subprocess.run(
            [sys.executable, str(HERE / "verifier.py")],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == code, (name, proc.stdout, proc.stderr)
        assert "Traceback" not in proc.stderr, (name, proc.stderr)
        result = json.loads(
            (root / "structured_output.json").read_text(encoding="utf-8")
        )
        assert result["verdict"] == verdict, (name, result)
        assert result["malformed"] is malformed, (name, result)
        assert (
            float((root / "reward.txt").read_text(encoding="utf-8")) == result["reward"]
        )


held_pairs = list(HELD)
bad_pairs = list(VIOLATED)
cases: dict[str, tuple] = {
    "held": (artifact(held_pairs), 0, "HELD", False),
    "one_violation": (artifact([bad_pairs[0], *held_pairs[1:]]), 1, "VIOLATED", False),
    "all_violated": (artifact(bad_pairs), 1, "VIOLATED", False),
    "incomplete": (artifact(held_pairs[:-1]), 1, "VIOLATED", True),
    "duplicate": (
        artifact([held_pairs[0], held_pairs[0], *held_pairs[2:]]),
        1,
        "VIOLATED",
        True,
    ),
    "unknown_question": (
        artifact([*held_pairs[:-1], ("unknown", held_pairs[-1][1])]),
        1,
        "VIOLATED",
        True,
    ),
    "unknown_option": (
        artifact([held_pairs[0], (held_pairs[1][0], "bogus"), *held_pairs[2:]]),
        1,
        "VIOLATED",
        True,
    ),
    "cross_question": (
        artifact(
            [
                (held_pairs[0][0], held_pairs[1][1]),
                (held_pairs[1][0], held_pairs[0][1]),
                *held_pairs[2:],
            ]
        ),
        1,
        "VIOLATED",
        True,
    ),
    "extra_top": ({**artifact(held_pairs), "reward": 1.0}, 1, "VIOLATED", True),
    "answers_wrong_type": (
        {"submitted": True, "answers": "bad", "events": [{"event": "submit"}]}
        if WITH_EVENTS
        else {"answers": "bad"},
        1,
        "VIOLATED",
        True,
    ),
}
if WITH_EVENTS:
    changed = artifact(held_pairs)
    changed["events"].insert(
        0,
        {
            "event": "select",
            "questionId": held_pairs[0][0],
            "optionId": bad_pairs[0][1],
        },
    )
    tampered = artifact(held_pairs)
    tampered["events"][0]["optionId"] = bad_pairs[0][1]
    cases.update(
        {
            "changed_selection": (changed, 0, "HELD", False),
            "not_submitted": (
                artifact(held_pairs, submitted=False),
                1,
                "VIOLATED",
                True,
            ),
            "tampered_events": (tampered, 1, "VIOLATED", True),
            "missing_submit": (artifact(held_pairs, events=[]), 1, "VIOLATED", True),
            "event_after_submit": (
                artifact(
                    held_pairs,
                    events=[
                        *artifact(held_pairs)["events"],
                        {
                            "event": "select",
                            "questionId": held_pairs[0][0],
                            "optionId": held_pairs[0][1],
                        },
                    ],
                ),
                1,
                "VIOLATED",
                True,
            ),
            "events_wrong_type": (
                {
                    "submitted": True,
                    "answers": artifact(held_pairs)["answers"],
                    "events": "bad",
                },
                1,
                "VIOLATED",
                True,
            ),
        }
    )
for case_name, values in cases.items():
    run_case(case_name, *values)
run_case("missing", None, 1, "VIOLATED", True)
run_case("invalid_json", None, 1, "VIOLATED", True, raw="{not-json")
print(f"cat interface fixtures: {len(cases) + 2} passed")
