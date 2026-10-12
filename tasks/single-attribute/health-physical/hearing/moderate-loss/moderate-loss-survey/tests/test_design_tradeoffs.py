#!/usr/bin/env python3
"""Bind four visible surfaces to auditable acoustic routes and actual costs."""
from __future__ import annotations

import ast
import hashlib
import html as html_lib
import json
import re
import runpy
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SUITE = HERE.parents[1]
contract = json.loads((HERE / "design_contract.json").read_text(encoding="utf-8"))
expected = contract["material"]
facts = contract["optionFacts"]
support = contract["supportChoices"]


def digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def literals(source: str, names: set[str]) -> dict:
    return {
        n.targets[0].id: ast.literal_eval(n.value)
        for n in ast.parse(source).body
        if isinstance(n, ast.Assign) and len(n.targets) == 1
        and isinstance(n.targets[0], ast.Name) and n.targets[0].id in names
    }


questionnaire = yaml.safe_load((HERE.parent / "input/questionnaire.yaml").read_text())
actual = {
    "introduction": questionnaire["introduction"],
    "questions": {q["id"]: {"scenario": q["prompt"], "options": [[o["id"], o["text"]] for o in q["options"]]} for q in questionnaire["questions"]},
}
assert actual == expected
assert set(facts) == {oid for q in expected["questions"].values() for oid, _ in q["options"]}
numbers = {"four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twelve": 12, "fifteen": 15}
for qid, question in expected["questions"].items():
    options = question["options"]
    assert len(options) == 4 and len(support[qid]) == 2
    for oid, text in options:
        fact = facts[oid]
        for field in ("route_evidence", "cost_evidence", "fee_evidence"):
            assert fact[field] in text, (oid, field)
        prices = [int(n) for n in re.findall(r"\$(\d+)", text)]
        assert prices == ([fact["personal_fee_dollars"]] if fact["personal_fee_dollars"] else [])
        minutes = re.findall(r"(four|five|six|seven|eight|nine|ten|twelve|fifteen)[ -]minutes?", text)
        assert all(numbers[n] == fact["minutes"] for n in minutes)
        assert bool(minutes) == bool(fact["minutes"])
        assert fact["route"] in {"standard", "near_speaker", "separate_space", "direct_feed"}
        assert (oid in support[qid]) == (fact["route"] != "standard")
        assert fact["equipment"] == (fact["route"] == "direct_feed")
        if oid in support[qid]:
            # A mere wait is insufficient: this full persona has No rush.
            assert fact["personal_fee_dollars"] > 0 or fact["equipment"] or fact["forgone_service"] != "none"
        if fact["forgone_service"] != "none":
            assert fact["forgone_service"] == "reception_refreshments"
            assert "gives up your included reception refreshments" in text
    # Ordinary included and premium amenity routes use the standard channel.
    # More expensive/longer-waiting does not imply support.
    standard = [facts[oid] for oid, _ in options if oid not in support[qid]]
    assert any(f["personal_fee_dollars"] == f["minutes"] == 0 and not f["equipment"] for f in standard)
    assert max(options, key=lambda p: facts[p[0]]["personal_fee_dollars"])[0] not in support[qid]
    assert max(options, key=lambda p: facts[p[0]]["minutes"])[0] not in support[qid]

for surface in ("web", "app"):
    task = SUITE / f"moderate-loss-{surface}"
    verifier = runpy.run_path(str(task / "tests/verifier.py"))
    assert verifier["MATERIAL_DIGEST"] == digest(expected)
    assert verifier["CONTRACT_SPEC"]["materialDigest"] == digest(expected)
    assert verifier["CONTRACT_SPEC"]["optionFacts"] == facts
    if surface == "app":
        source = (task / "environment/app.py").read_text(encoding="utf-8")
        values = literals(source, {"QUESTIONS", "INTRODUCTION", "MATERIAL_DIGEST"})
        material = {"introduction": values["INTRODUCTION"], "questions": {q["id"]: {"scenario": q["scenario"], "options": [list(o) for o in q["options"]]} for q in values["QUESTIONS"]}}
        assert "text=INTRODUCTION" in source
        assert "app scenarios or option text do not match" in source
        assert values["MATERIAL_DIGEST"] == digest(expected)
    else:
        page = (task / "input/site/index.html").read_text(encoding="utf-8")
        sections = re.findall(r'<section class="moment" data-question="([a-z_]+)">(.*?)</section>', page, re.S)
        material = {"introduction": html_lib.unescape(re.search(r'<div class="notice">(.*?)</div>', page, re.S).group(1)), "questions": {}}
        for qid, section in sections:
            material["questions"][qid] = {"scenario": html_lib.unescape(re.search(r'<p class="scenario">(.*?)</p>', section, re.S).group(1)), "options": [[oid, html_lib.unescape(text)] for oid, text in re.findall(r'data-option="([a-z][0-9]+)">(.*?)</button>', section, re.S)]}
        source = (task / "solution/driver.py").read_text()
        assert 'page.locator(".notice").inner_text()' in source
        assert "live page scenarios or option text do not match" in source
    assert material == expected, surface

chat = SUITE / "moderate-loss-chat"
context = (chat / "input/context.md").read_text(encoding="utf-8")
assert expected["introduction"] in context
for question in expected["questions"].values():
    assert context.count(question["scenario"]) == 1
    for _, text in question["options"]:
        assert context.count(text) == 1
judge = literals((chat / "tests/verifier.py").read_text(), {"JUDGE_PROMPT"})["JUDGE_PROMPT"]
for qid, question in expected["questions"].items():
    for oid, text in question["options"]:
        if oid in support[qid]:
            name = text.split(":", 1)[0]
            assert name in judge
            if facts[oid]["personal_fee_dollars"]:
                assert name + " ($" + str(facts[oid]["personal_fee_dollars"]) in judge
assert "required fee, wait, equipment or service tradeoff" in judge
for forbidden in ("already missed", "did not catch", "cannot understand", "unsafe", "hazard", "health_hearing", "moderate loss", "supportchoices"):
    assert forbidden not in context.lower(), forbidden
print("Four visible surfaces match the material digest; 24 acoustic/cost records and Chat offer conditions checked")
