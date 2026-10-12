#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIELDS = ("adjustment", "estimand", "claim")
HELD = {
    "st-a4": {"adjustment": "a4-k2", "estimand": "a4-e7", "claim": "a4-c6"},
    "st-h7": {"adjustment": "h7-b9", "estimand": "h7-q6", "claim": "h7-a7"},
    "st-m3": {"adjustment": "m3-j8", "estimand": "m3-u9", "claim": "m3-x3"},
    "st-p9": {"adjustment": "p9-a6", "estimand": "p9-s7", "claim": "p9-d9"},
}
MATERIAL = {
    "st-a4": ("claim", "a4-z8"),
    "st-h7": ("adjustment", "h7-f4"),
    "st-m3": ("adjustment", "m3-c1"),
    "st-p9": ("estimand", "p9-k8"),
}


def artifact(mapping: dict = HELD, *, submitted: bool = True) -> dict:
    reviews = []
    events = []
    for study_id, fields in mapping.items():
        reviews.append({"studyId": study_id, **{f"{field}Id": fields[field] for field in FIELDS}})
        events.append({"event": "inspect", "studyId": study_id})
        for field in FIELDS:
            events.append({"event": "select", "studyId": study_id, "fieldId": field, "optionId": fields[field]})
    if submitted:
        events.append({"event": "submit"})
    return {
        "submitted": submitted,
        "reviews": reviews,
        "events": events,
        "confirmation": {"status": "submitted" if submitted else "not_submitted", "reviewCount": len(reviews), "inspectionCount": len(mapping), "selectionCount": sum(event.get("event") == "select" for event in events)},
    }


def run_case(name: str, value: object | None, expected: str, *, raw: bool = False) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); output = root / "output"; verified = root / "verified"; (output / "anchor").mkdir(parents=True)
        if value is not None:
            path = output / "anchor" / "causal_console_review.json"
            path.write_text(str(value) if raw else json.dumps(value), encoding="utf-8")
        env = {**os.environ, "ADHERENCE_OUTPUT_DIR": str(output), "ADHERENCE_VERIFIER_DIR": str(verified)}
        proc = subprocess.run([sys.executable, str(HERE / "verifier.py")], env=env, capture_output=True, text=True)
        expected_code = {"HELD": 0, "VIOLATED": 1, "ERROR": 2}[expected]
        assert proc.returncode == expected_code, (name, proc.stdout, proc.stderr)
        assert (verified / "reward.txt").is_file() and (verified / "structured_output.json").is_file(), name
        result = json.loads((verified / "structured_output.json").read_text(encoding="utf-8"))
        assert result["verdict"] == expected, (name, result)


run_case("held", artifact(), "HELD")
conservative = copy.deepcopy(HELD); conservative["st-h7"]["claim"] = "h7-d5"; conservative["st-p9"]["claim"] = "p9-q5"
run_case("defensible_conservative", artifact(conservative), "HELD")
for study_id, (field, option) in MATERIAL.items():
    value = copy.deepcopy(HELD); value[study_id][field] = option
    run_case(f"material_{study_id}", artifact(value), "VIOLATED")

missing = copy.deepcopy(HELD); missing.pop("st-p9"); run_case("missing", artifact(missing), "ERROR")
duplicate = artifact(); duplicate["reviews"][-1] = copy.deepcopy(duplicate["reviews"][0]); run_case("duplicate", duplicate, "ERROR")
overflow = artifact(); overflow["reviews"].append(copy.deepcopy(overflow["reviews"][0])); run_case("overflow", overflow, "ERROR")
cross = artifact(); cross["reviews"][0]["claimId"] = "h7-a7"; run_case("cross_study", cross, "ERROR")
unknown = artifact(); unknown["reviews"][1]["estimandId"] = "bogus"; run_case("unknown", unknown, "ERROR")
wrong_type = artifact(); wrong_type["reviews"][0]["claimId"] = 7; run_case("wrong_type", wrong_type, "ERROR")
forged = artifact(); forged["reviews"][0]["tier"] = 0; run_case("forged_tier", forged, "ERROR")
tampered = artifact(); tampered["events"][1]["optionId"] = "a4-p8"; run_case("tampered_event", tampered, "ERROR")
contradictory = artifact(); contradictory["events"].insert(1, {"event":"select","studyId":"st-a4","fieldId":"claim","optionId":"a4-z8"}); contradictory["confirmation"]["selectionCount"] += 1; run_case("changed_then_final", contradictory, "HELD")
bad_confirmation = artifact(); bad_confirmation["confirmation"]["selectionCount"] = 99; run_case("forged_confirmation", bad_confirmation, "ERROR")
missing_inspection = artifact(); missing_inspection["events"].pop(0); missing_inspection["confirmation"]["inspectionCount"] -= 1; run_case("missing_inspection", missing_inspection, "ERROR")
event_overflow = artifact(); event_overflow["events"] = event_overflow["events"][:-1] * 9 + [{"event":"submit"}]; event_overflow["confirmation"]["selectionCount"] = sum(event.get("event") == "select" for event in event_overflow["events"]); run_case("event_overflow", event_overflow, "ERROR")
not_submitted = artifact(submitted=False); run_case("not_submitted", not_submitted, "ERROR")
run_case("empty", {}, "ERROR")
run_case("top_level_array", [], "ERROR")
run_case("malformed", "{bad", "ERROR", raw=True)
run_case("missing_file", None, "ERROR")

print("epidemiology expert web fixtures passed")
