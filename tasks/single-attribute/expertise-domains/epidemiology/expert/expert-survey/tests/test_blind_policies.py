#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
questionnaire = yaml.safe_load((HERE.parent / "input" / "questionnaire.yaml").read_text(encoding="utf-8"))
key = yaml.safe_load((HERE / "answer_key.yaml").read_text(encoding="utf-8"))["tiers"]
questions = questionnaire["questions"]

assert len(questions) == 6
assert {question["id"] for question in questions} == set(key)

tier_zero_positions = []
for question in questions:
    options = question["options"]
    assert len(options) == 4
    lengths = [len(option["text"]) for option in options]
    assert min(lengths) >= 110, (question["id"], lengths)
    assert max(lengths) - min(lengths) <= 80, (question["id"], lengths)
    tiers = [key[question["id"]][option["id"]] for option in options]
    assert tiers.count(0) == 1
    tier_zero_positions.append(tiers.index(0))

for position in range(4):
    fixed_policy_tiers = [
        key[question["id"]][question["options"][position]["id"]]
        for question in questions
    ]
    assert any(tier >= 2 for tier in fixed_policy_tiers), (position, fixed_policy_tiers)
assert set(tier_zero_positions) == {0, 1, 2, 3}

longest_policy_tiers = []
for question in questions:
    longest = max(question["options"], key=lambda option: len(option["text"]))
    longest_policy_tiers.append(key[question["id"]][longest["id"]])
assert any(tier >= 2 for tier in longest_policy_tiers), longest_policy_tiers

randomized = questions[0]
association_only = next(option for option in randomized["options"] if option["id"] == "z4q")
assert "association" in association_only["text"].lower()
assert key[randomized["id"]][association_only["id"]] == 1
registry = questions[1]
unsupported_causal = next(option for option in registry["options"] if "causal" in option["text"].lower())
assert key[registry["id"]][unsupported_causal["id"]] >= 2

# Keep the task from regressing to lexical caricatures that reveal a wrong
# answer without requiring the design/estimand comparison.
visible_text = " ".join(
    option["text"].lower() for question in questions for option in question["options"]
)
for shortcut in (
    "no study can",
    "guarantees transportability",
    "proof that",
    "extrapolate the full-population effect anyway",
    "add every descendant",
    "cannot change the estimand",
    "removes all mediator bias",
    "any adjustment invalidates",
    "ignore spillovers",
    "automatically creates independent",
):
    assert shortcut not in visible_text, shortcut

random_pass = math.prod(
    sum(tier <= 1 for tier in key[question["id"]].values())
    / len(key[question["id"]])
    for question in questions
)
assert math.isclose(random_pass, 0.00390625, rel_tol=0, abs_tol=1e-18)

print("epidemiology expert survey blind-policy checks passed")
