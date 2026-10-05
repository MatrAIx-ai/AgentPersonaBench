#!/usr/bin/env python3
"""Score-gradient and fail-closed fixtures for a strict Survey verifier."""
import copy
import hashlib
import importlib.util
import itertools
import json
import os
import tempfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("survey_verifier", HERE / "verifier.py")
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


def evaluate(payload=None, raw=None):
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        if raw is not None:
            (out / "survey_result.json").write_text(raw, encoding="utf-8")
        elif payload is not None:
            (out / "survey_result.json").write_text(json.dumps(payload), encoding="utf-8")
        old_od = os.environ.get("ADHERENCE_OUTPUT_DIR")
        old_vd = os.environ.get("ADHERENCE_VERIFIER_DIR")
        os.environ["ADHERENCE_OUTPUT_DIR"] = str(out)
        os.environ["ADHERENCE_VERIFIER_DIR"] = str(out / "verifier")
        try:
            try:
                verifier.main()
                rc = 0
            except SystemExit as exc:
                rc = int(exc.code or 0)
            result = json.loads((out / "verifier" / "structured_output.json").read_text())
        finally:
            if old_od is None: os.environ.pop("ADHERENCE_OUTPUT_DIR", None)
            else: os.environ["ADHERENCE_OUTPUT_DIR"] = old_od
            if old_vd is None: os.environ.pop("ADHERENCE_VERIFIER_DIR", None)
            else: os.environ["ADHERENCE_VERIFIER_DIR"] = old_vd
        return rc, result


structure, key = verifier.load_contract()
labels = [check[1] for check in verifier.CHECKS]
qids = sorted(structure)


def choice(qid, first, second):
    return next(oid for oid in structure[qid]
                if key[labels[0]][oid] is first and key[labels[1]][oid] is second)


def artifact(first, second):
    return {"answers": [{"questionId": qid, "selectedOptionId": choice(qid, first, second)}
                        for qid in qids]}


for states, score in [((True, True), 2), ((True, False), 1),
                      ((False, True), 1), ((False, False), 0)]:
    rc, result = evaluate(artifact(*states))
    assert rc == 0 and result["reward"] == score and len(result["checks"]) == 2

full_count = sum(
    all(all(key[label][oid] for oid in picks) for label in labels)
    for picks in itertools.product(*(structure[qid] for qid in qids))
)
assert full_count == 1
for states in [(False, True), (True, False), (False, False)]:
    tampered = artifact(True, True)
    tampered["answers"][2]["selectedOptionId"] = choice("q3", *states)
    rc, result = evaluate(tampered)
    assert rc == 0 and result["reward"] == sum(states)

valid = artifact(True, True)
bad_artifacts = [
    (None, None), (None, "{"), ([], None), ({}, None),
    ({"answers": valid["answers"][:-1]}, None),
    ({"answers": valid["answers"] + [valid["answers"][0]]}, None),
    ({"answers": valid["answers"], "extra": 1}, None),
    ({"answers": [{"questionId": qids[0], "selectedOptionId": choice(qids[1], True, True)},
                  *valid["answers"][1:]]}, None),
    ({"answers": [{"questionId": "forged", "selectedOptionId": "forged"},
                  *valid["answers"][1:]]}, None),
]
for payload, raw in bad_artifacts:
    rc, result = evaluate(payload=payload, raw=raw)
    assert rc != 0 and result["reward"] == 0


def rejected_contract(questionnaire, answer_key):
    with tempfile.TemporaryDirectory() as td:
        qpath, kpath = Path(td) / "questionnaire.yaml", Path(td) / "answer_key.yaml"
        qpath.write_text(yaml.safe_dump(questionnaire, sort_keys=False), encoding="utf-8")
        kpath.write_text(yaml.safe_dump(answer_key, sort_keys=False), encoding="utf-8")
        old_hash = verifier.QUESTIONNAIRE_SHA256
        verifier.QUESTIONNAIRE_SHA256 = hashlib.sha256(qpath.read_bytes()).hexdigest()
        try:
            try:
                verifier.load_contract(qpath, kpath)
            except verifier.ContractError:
                return
            raise AssertionError("corrupt questionnaire/key was accepted")
        finally:
            verifier.QUESTIONNAIRE_SHA256 = old_hash


questionnaire = yaml.safe_load(verifier.QPATH.read_text(encoding="utf-8"))
bad_q = copy.deepcopy(questionnaire); bad_q["questions"][0]["extra"] = 1
rejected_contract(bad_q, copy.deepcopy(key))
bad_q = copy.deepcopy(questionnaire); bad_q["questions"][1]["options"][0]["id"] = bad_q["questions"][0]["options"][0]["id"]
rejected_contract(bad_q, copy.deepcopy(key))
bad_q = copy.deepcopy(questionnaire); bad_q["questions"][0]["options"].pop()
rejected_contract(bad_q, copy.deepcopy(key))
bad_key = copy.deepcopy(key); bad_key[labels[0]].pop(next(iter(bad_key[labels[0]])))
rejected_contract(copy.deepcopy(questionnaire), bad_key)
bad_key = copy.deepcopy(key); bad_key[labels[0]][next(iter(bad_key[labels[0]]))] = 1
rejected_contract(copy.deepcopy(questionnaire), bad_key)
bad_key = copy.deepcopy(key); bad_key["extra"] = {}
rejected_contract(copy.deepcopy(questionnaire), bad_key)

with tempfile.TemporaryDirectory() as td:
    qpath = Path(td) / "questionnaire.yaml"
    qpath.write_bytes(verifier.QPATH.read_bytes().replace(b"Which", b"Choose", 1))
    try:
        verifier.load_contract(qpath, verifier.KEYPATH)
    except verifier.ContractError:
        pass
    else:
        raise AssertionError("questionnaire text drift was accepted")

print("PASS: Survey 2/1/1/0, strict artifact/schema/key/source fixtures")


def test_fixture_contracts():
    assert True
