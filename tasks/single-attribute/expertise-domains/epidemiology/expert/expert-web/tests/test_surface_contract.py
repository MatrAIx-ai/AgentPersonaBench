#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
html = (HERE.parent / "input" / "site" / "index.html").read_text(encoding="utf-8")
key = yaml.safe_load((HERE / "answer_key.yaml").read_text(encoding="utf-8"))["tiers"]

assert "window.__artifact" in html
assert "addEventListener(\"click\"" in html
assert "events.push({event:\"select\"" in html
assert "events.push({event:\"submit\"})" in html
assert "events.push({event:\"inspect\",studyId})" in html

study_ids = re.findall(r'<section class="study" data-study="([^"]+)"', html)
assert study_ids == ["st-a4", "st-h7", "st-m3", "st-p9"]
for study_id in study_ids:
    for field_id in ("adjustment", "estimand", "claim"):
        options = re.findall(
            rf'<button class="choice" data-study="{study_id}" data-field="{field_id}" '
            rf'data-option="([^"]+)">(.*?)</button>',
            html,
            re.S,
        )
        ids = {option_id for option_id, _ in options}
        assert ids == set(key[study_id][field_id]), (study_id, field_id, ids)
        lengths = [len(re.sub(r"<.*?>", "", text).strip()) for _, text in options]
        assert min(lengths) >= 70, (study_id, field_id, lengths)
        assert max(lengths) - min(lengths) <= 85, (study_id, field_id, lengths)

lower = html.lower()
for forbidden in ("data-tier", "data-score", "data-expected", "ground_truth", "answer_key"):
    assert forbidden not in lower, forbidden

# These phrases previously made distractors rejectable by tone alone. Keep
# every choice professional enough that the user must reconcile design,
# adjustment, estimand, target, and claim.
choice_text = " ".join(
    re.sub(r"<.*?>", "", value).lower()
    for value in re.findall(r'<button class="choice"[^>]*>(.*?)</button>', html, re.S)
)
for shortcut in (
    "randomization cannot support",
    "universal causal effect",
    "automatically causal",
    "predictors always reduce bias",
    "prevents any causal interpretation",
    "statistical significance establishes positivity",
    "because model-based predictions exist",
):
    assert shortcut not in choice_text, shortcut

driver = (HERE.parent / "solution" / "driver.py").read_text(encoding="utf-8").lower()
assert "playwright" in driver and ".click()" in driver
assert "answer_key" not in driver and "tiers" not in driver

print("epidemiology expert web surface contract passed")
