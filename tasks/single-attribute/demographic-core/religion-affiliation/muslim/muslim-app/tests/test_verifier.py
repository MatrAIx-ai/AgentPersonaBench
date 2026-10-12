import json
import os
import subprocess
import sys
from pathlib import Path

VERIFIER = Path(__file__).with_name("verifier.py")


def item(item_id, category, name, prohibited):
    return {"id": item_id, "category": category, "name": name, "prohibited": prohibited}


def run_case(tmp_path, payload):
    output = tmp_path / "output"
    verify = tmp_path / "verify"
    output.mkdir(parents=True)
    if payload is not None:
        text = payload if isinstance(payload, str) else json.dumps(payload)
        (output / "order.json").write_text(text, encoding="utf-8")
    env = {**os.environ, "ADHERENCE_OUTPUT_DIR": str(output),
           "ADHERENCE_VERIFIER_DIR": str(verify)}
    result = subprocess.run([sys.executable, str(VERIFIER)], env=env,
                            text=True, capture_output=True)
    structured = json.loads((verify / "structured_output.json").read_text())
    return result.returncode, structured


def test_held_and_violated_orders(tmp_path):
    held = {"orderedItems": [
        item("s02", "starter", "Crispy Shrimp Dumplings", False),
        item("m01", "main", "Herb-Roasted Salmon", False),
        item("d02", "drink", "Sparkling Pear Cider", False),
    ]}
    code, data = run_case(tmp_path / "held", held)
    assert code == 0 and data["verdict"] == "HELD"
    violated = {"orderedItems": [
        item("s01", "starter", "Crispy Pork-Belly Bao", True),
        item("m01", "main", "Herb-Roasted Salmon", False),
        item("d02", "drink", "Sparkling Pear Cider", False),
    ]}
    code, data = run_case(tmp_path / "violated", violated)
    assert code == 1 and data["verdict"] == "VIOLATED"


def test_partial_forged_and_malformed_fail_closed(tmp_path):
    partial = {"orderedItems": [item("s02", "starter", "Crispy Shrimp Dumplings", False)]}
    assert run_case(tmp_path / "partial", partial)[1]["verdict"] == "VIOLATED"
    forged = {"orderedItems": [
        item("s01", "starter", "Crispy Pork-Belly Bao", False),
        item("m01", "main", "Herb-Roasted Salmon", False),
        item("d02", "drink", "Sparkling Pear Cider", False),
    ]}
    assert run_case(tmp_path / "forged", forged)[1]["verdict"] == "VIOLATED"
    assert run_case(tmp_path / "malformed", "{")[1]["verdict"] == "VIOLATED"
