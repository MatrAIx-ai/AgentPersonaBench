#!/usr/bin/env python3
"""Score-gradient, artifact, source/key, and exact-three UI fixtures for App."""
import ast
import copy
import importlib.util
import json
import os
import tempfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("app_verifier", HERE / "verifier.py")
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)
items = verifier.load_catalog()


def evaluate(payload=None, raw=None):
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        if raw is not None:
            (out / "selection.json").write_text(raw, encoding="utf-8")
        elif payload is not None:
            (out / "selection.json").write_text(json.dumps(payload), encoding="utf-8")
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


labels = list(verifier.LABELS)


def ids_for(a, b):
    return [oid for oid, row in items.items() if row[labels[0]] is a and row[labels[1]] is b][:3]


def payload_for(picks, persona=None):
    return {"persona": verifier.PERSONA if persona is None else persona,
            "selectedPlans": [{"id": oid, "name": items.get(oid, {}).get("name", "forged")}
                              for oid in picks]}


for states, score in [((True, True), 2), ((True, False), 1),
                      ((False, True), 1), ((False, False), 0)]:
    picks = ids_for(*states)
    assert len(picks) == 3
    rc, result = evaluate(payload_for(picks))
    assert rc == 0 and result["reward"] == score and len(result["checks"]) == 2

known = list(items)
forged_name = payload_for(known[:3]); forged_name["selectedPlans"][0]["name"] = "forged"
extra_row = payload_for(known[:3]); extra_row["selectedPlans"][0]["extra"] = 1
bad_artifacts = [
    (None, None), (None, "{"), ([], None), ({}, None),
    (payload_for(known[:1]), None), (payload_for(known[:4]), None),
    (payload_for([known[0], known[0], known[1]]), None),
    (payload_for([known[0], known[1], "forged"]), None),
    (forged_name, None), (extra_row, None),
    (dict(payload_for(known[:3]), extra=1), None),
    (payload_for(known[:3], persona="forged"), None),
]
for payload, raw in bad_artifacts:
    rc, result = evaluate(payload=payload, raw=raw)
    assert rc != 0 and result["reward"] == 0


def rejected(source_text, key_data):
    with tempfile.TemporaryDirectory() as td:
        source, key = Path(td) / "choiceapp.py", Path(td) / "answer_key.yaml"
        source.write_text(source_text, encoding="utf-8")
        key.write_text(yaml.safe_dump(key_data, sort_keys=False), encoding="utf-8")
        try:
            verifier.load_catalog(source, key)
        except verifier.ContractError:
            return
        raise AssertionError("corrupt app/key was accepted")


source_text = verifier.APP_SOURCE.read_text(encoding="utf-8")
key_data = yaml.safe_load(verifier.KEY.read_text(encoding="utf-8"))
first = next(iter(key_data["items"]))
tree = ast.parse(source_text)
menu = next(ast.literal_eval(node.value) for node in ast.walk(tree)
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "MENU"
                                                     for target in node.targets))
first_text = menu[0][3]
rejected(source_text.replace(f"('{first}',", "('drift',", 1), copy.deepcopy(key_data))
rejected(source_text.replace(key_data["items"][first]["name"], "Renamed card", 1), copy.deepcopy(key_data))
rejected(source_text.replace(first_text, first_text + " changed", 1), copy.deepcopy(key_data))
bad = copy.deepcopy(key_data); bad["items"].pop(first); rejected(source_text, bad)
bad = copy.deepcopy(key_data); bad["items"]["ghost"] = copy.deepcopy(key_data["items"][first]); rejected(source_text, bad)
bad = copy.deepcopy(key_data); bad["items"][first][labels[0]] = 1; rejected(source_text, bad)
bad = copy.deepcopy(key_data); bad["items"][first][labels[0]] = not bad["items"][first][labels[0]]; rejected(source_text, bad)
bad = copy.deepcopy(key_data); bad["items"][first]["name"] = "forged"; rejected(source_text, bad)
bad = copy.deepcopy(key_data); bad["items"][first]["text_sha256"] = "0" * 64; rejected(source_text, bad)
bad = copy.deepcopy(key_data); bad["items"][first]["extra"] = False; rejected(source_text, bad)

# Exercise the app's submit gate without opening a display.
app_spec = importlib.util.spec_from_file_location("choice_app", verifier.APP_SOURCE)
app_module = importlib.util.module_from_spec(app_spec)
app_spec.loader.exec_module(app_module)
for count in (1, 4):
    with tempfile.TemporaryDirectory() as td:
        old_output = app_module.OUTPUT_DIR
        app_module.OUTPUT_DIR = td
        instance = app_module.App.__new__(app_module.App)
        instance.picks = known[:count]
        instance.submit()
        assert not (Path(td) / "selection.json").exists(), f"UI wrote artifact for {count} picks"
        app_module.OUTPUT_DIR = old_output

print("PASS: App 2/1/1/0, exact-three UI, strict artifact/source-key fixtures")


def test_fixture_contracts():
    assert True
