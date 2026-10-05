#!/usr/bin/env python3
"""Positive/negative fixtures for the strict Survey verifier."""
import copy
import importlib.util
import json
import os
import tempfile
from pathlib import Path
import yaml

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("task_verifier", HERE / "verifier.py")
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)
structure = verifier._load_structure()
maps = verifier._load_label_maps(structure)


def evaluate(payload=None, raw=None):
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        if raw is not None:
            (out / "survey_result.json").write_text(raw, encoding="utf-8")
        elif payload is not None:
            (out / "survey_result.json").write_text(json.dumps(payload), encoding="utf-8")
        old_od, old_vd = os.environ.get("ADHERENCE_OUTPUT_DIR"), os.environ.get("ADHERENCE_VERIFIER_DIR")
        os.environ["ADHERENCE_OUTPUT_DIR"] = str(out)
        os.environ["ADHERENCE_VERIFIER_DIR"] = str(out / "verifier")
        try:
            try:
                verifier.main()
            except SystemExit as exc:
                rc = int(exc.code or 0)
            result = json.loads((out / "verifier" / "structured_output.json").read_text())
        finally:
            if old_od is None: os.environ.pop("ADHERENCE_OUTPUT_DIR", None)
            else: os.environ["ADHERENCE_OUTPUT_DIR"] = old_od
            if old_vd is None: os.environ.pop("ADHERENCE_VERIFIER_DIR", None)
            else: os.environ["ADHERENCE_VERIFIER_DIR"] = old_vd
        return rc, result


def payload_for(a_ok, b_ok):
    (na, la, oka), (nb, lb, okb) = verifier.CHECKS
    answers = []
    for qid, ids in structure.items():
        oid = next(oid for oid in ids
                   if (maps[la][oid] == oka) == a_ok and (maps[lb][oid] == okb) == b_ok)
        answers.append({"questionId": qid, "selectedOptionId": oid})
    return {"answers": answers}


for cell, score in [((True, True), 2), ((True, False), 1),
                    ((False, True), 1), ((False, False), 0)]:
    rc, result = evaluate(payload_for(*cell))
    assert result["reward"] == score and len(result["checks"]) == 2

valid = payload_for(True, True)
bad_cases = [
    (None, None),
    ({"answers": []}, None),
    (None, "{"),
    ({"answers": valid["answers"][:1]}, None),
    ({"answers": [valid["answers"][0], valid["answers"][0], valid["answers"][2]]}, None),
    ({"answers": [dict(valid["answers"][0], selectedOptionId="forged"),
                  *valid["answers"][1:]]}, None),
    ({"answers": valid["answers"], "extra": 1}, None),
    ({"answers": [dict(valid["answers"][0], selectedOptionId=valid["answers"][1]["selectedOptionId"]),
                  *valid["answers"][1:]]}, None),
]
for payload, raw in bad_cases:
    rc, result = evaluate(payload, raw)
    assert rc != 0 and result["reward"] == 0

key = yaml.safe_load(verifier._KEYPATH.read_text())
first_label = verifier.CHECKS[0][1]
first_id = next(iter(key[first_label]))
for name, mutate in [
    ("missing", lambda d: d[first_label].pop(first_id)),
    ("extra", lambda d: d[first_label].__setitem__("ghost", False)),
    ("non-bool", lambda d: d[first_label].__setitem__(first_id, "false")),
]:
    broken = copy.deepcopy(key)
    mutate(broken)
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "key.yaml"
        path.write_text(yaml.safe_dump(broken), encoding="utf-8")
        try:
            verifier._load_label_maps(structure, path)
        except verifier.ContractError:
            continue
        raise AssertionError(f"{name} host-key corruption accepted")

print("PASS: Survey 2/1/1/0 and strict negative fixtures")

def test_fixture_contracts():
    """Collection succeeds only after the module-level contract probes pass."""
    assert True
