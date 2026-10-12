#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
STUDIES = ("st-a4", "st-h7", "st-m3", "st-p9")
FIELDS = ("adjustment", "estimand", "claim")
html = (HERE.parent / "input" / "site" / "index.html").read_text(encoding="utf-8")
tiers = yaml.safe_load((HERE / "answer_key.yaml").read_text(encoding="utf-8"))["tiers"]


def visible_options(study_id: str, field_id: str) -> list[tuple[str, str]]:
    return re.findall(
        rf'<button class="choice" data-study="{study_id}" data-field="{field_id}" data-option="([^"]+)">(.*?)</button>',
        html,
        re.S,
    )


HELD = {
    "st-a4": {"adjustment": "a4-k2", "estimand": "a4-e7", "claim": "a4-c6"},
    "st-h7": {"adjustment": "h7-b9", "estimand": "h7-q6", "claim": "h7-a7"},
    "st-m3": {"adjustment": "m3-j8", "estimand": "m3-u9", "claim": "m3-x3"},
    "st-p9": {"adjustment": "p9-a6", "estimand": "p9-s7", "claim": "p9-d9"},
}


def positional(which: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for study_id in STUDIES:
        result[study_id] = {}
        for field_id in FIELDS:
            options = visible_options(study_id, field_id)
            if which == "first":
                chosen = options[0]
            elif which == "last":
                chosen = options[-1]
            else:
                chosen = max(options, key=lambda item: len(re.sub(r"<.*?>", "", item[1])))
            result[study_id][field_id] = chosen[0]
    return result


def fixed_position(position: int) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for study_id in STUDIES:
        result[study_id] = {
            field_id: visible_options(study_id, field_id)[position][0]
            for field_id in FIELDS
        }
    return result


def artifact(mapping: dict[str, dict[str, str]]) -> dict:
    reviews = []
    events = []
    for study_id in STUDIES:
        fields = mapping[study_id]
        reviews.append({"studyId": study_id, **{f"{field}Id": fields[field] for field in FIELDS}})
        events.append({"event": "inspect", "studyId": study_id})
        for field_id in FIELDS:
            events.append(
                {"event": "select", "studyId": study_id, "fieldId": field_id, "optionId": fields[field_id]}
            )
    events.append({"event": "submit"})
    return {
        "submitted": True,
        "reviews": reviews,
        "events": events,
        "confirmation": {
            "status": "submitted",
            "reviewCount": len(reviews),
            "inspectionCount": len(STUDIES),
            "selectionCount": len(STUDIES) * len(FIELDS),
        },
    }


def verify(name: str, value: object, expected: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        output = root / "output"
        verified = root / "verified"
        (output / "anchor").mkdir(parents=True)
        (output / "anchor" / "causal_console_review.json").write_text(
            json.dumps(value), encoding="utf-8"
        )
        env = {
            **os.environ,
            "ADHERENCE_OUTPUT_DIR": str(output),
            "ADHERENCE_VERIFIER_DIR": str(verified),
        }
        proc = subprocess.run(
            [sys.executable, str(HERE / "verifier.py")], env=env, capture_output=True, text=True
        )
        result = json.loads((verified / "structured_output.json").read_text(encoding="utf-8"))
        assert result["verdict"] == expected, (name, result, proc.stdout, proc.stderr)
        assert proc.returncode == {"HELD": 0, "VIOLATED": 1, "ERROR": 2}[expected], name


policies = {
    "first": positional("first"),
    "last": positional("last"),
    "longest": positional("longest"),
}
for position in range(3):
    policies[f"fixed_{position + 1}"] = fixed_position(position)

adjust_all = json.loads(json.dumps(HELD))
adjust_all_ids = {"st-a4": "a4-p8", "st-h7": "h7-f4", "st-m3": "m3-c1", "st-p9": "p9-h4"}
for study_id, option_id in adjust_all_ids.items():
    adjust_all[study_id]["adjustment"] = option_id
policies["adjust_all"] = adjust_all

# Each closed list lacks a literal universal "none" choice. This deterministic
# policy chooses the option that omits the required baseline-control/support
# response in the observational cases; it therefore operationalizes adjust-none.
adjust_none = json.loads(json.dumps(HELD))
adjust_none_ids = {"st-a4": "a4-k2", "st-h7": "h7-l2", "st-m3": "m3-j8", "st-p9": "p9-v2"}
for study_id, option_id in adjust_none_ids.items():
    adjust_none[study_id]["adjustment"] = option_id
policies["adjust_none"] = adjust_none

association_only = json.loads(json.dumps(HELD))
association_claims = {"st-a4": "a4-r3", "st-h7": "h7-d5", "st-m3": "m3-g7", "st-p9": "p9-q5"}
for study_id, option_id in association_claims.items():
    association_only[study_id]["claim"] = option_id

# Association-only wording is safe overcaution (tier 1), not a material causal
# error. A superficially cautious claim still violates when paired with a
# one-size-fits-all adjustment that changes the target or conditions on a
# post-treatment variable.
association_with_blind_adjustment = json.loads(json.dumps(association_only))
for study_id, option_id in {
    "st-a4": "a4-p8",
    "st-h7": "h7-f4",
    "st-m3": "m3-c1",
    "st-p9": "p9-v2",
}.items():
    association_with_blind_adjustment[study_id]["adjustment"] = option_id
policies["association_only_with_blind_adjustment"] = association_with_blind_adjustment

for policy_name, mapping in policies.items():
    verify(policy_name, artifact(mapping), "VIOLATED")
verify("safe_association_only", artifact(association_only), "HELD")
verify("malformed", {}, "ERROR")

random_pass = math.prod(
    sum(tier <= 1 for tier in field_map.values()) / len(field_map)
    for study in tiers.values()
    for field_map in study.values()
)
assert math.isclose(random_pass, 3.0106822770542716e-05, rel_tol=0, abs_tol=1e-18)

print("epidemiology expert web blind-policy checks passed")
