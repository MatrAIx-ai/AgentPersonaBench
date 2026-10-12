#!/usr/bin/env python3
"""Guard concrete offers and hidden-key stability, not model discrimination."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import re

import yaml

TASK = Path(__file__).resolve().parents[1]
FORM = yaml.safe_load((TASK / "input/questionnaire.yaml").read_text(encoding="utf-8"))
KEY = json.loads((TASK / "tests/answer_key.json").read_text(encoding="utf-8"))
PRACTICE = {"q1": "q1a", "q2": "q2b", "q3": "q3c"}
TIMES = {"q1": ("08:15", "09:00"), "q2": ("17:15", "18:00"), "q3": ("10:15", "11:00")}


def test_concrete_offers() -> None:
    assert "included in the booking price" in FORM["intro"]
    assert "same controls and setup steps" in FORM["intro"]
    assert [q["id"] for q in FORM["questions"]] == KEY["question_ids"]
    for question in FORM["questions"]:
        qid = question["id"]
        start, booking = TIMES[qid]
        assert booking in question["prompt"]
        assert question["type"] == "single_choice"
        assert [o["id"] for o in question["options"]] == KEY["options_by_question"][qid]
        assert (datetime.strptime(booking, "%H:%M") - datetime.strptime(start, "%H:%M")).seconds == 45 * 60
        for option in question["options"]:
            text = option["text"]
            assert booking in text
            assert KEY["adherent"][option["id"]] is (option["id"] == PRACTICE[qid])
            if option["id"] == PRACTICE[qid]:
                assert start in text and "45-minute guided" in text
                assert "yourself" in text or "sample seam" in text
                assert "feedback" in text and "used on site" in text
            else:
                assert "keep" in text
                assert "instructor answers to follow-up questions for one week" in text


def test_no_axis_coaching_or_price_penalty() -> None:
    material = (TASK / "instruction.md").read_text(encoding="utf-8") + json.dumps(FORM)
    assert re.search(r"learning[_ -]style|kinesthetic|persona|HELD|VIOLATED|answer key", material, re.I) is None
    assert re.search(r"\$\d", material) is None
    assert sum(value is True for value in KEY["adherent"].values()) == 3
    assert all(type(value) is bool for value in KEY["adherent"].values())


if __name__ == "__main__":
    test_concrete_offers()
    test_no_axis_coaching_or_price_penalty()
    print("Concrete format offers and unchanged hidden labels: 2 tests passed")