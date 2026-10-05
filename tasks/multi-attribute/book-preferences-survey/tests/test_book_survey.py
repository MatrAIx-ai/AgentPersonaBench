from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
import yaml

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("book_survey_verifier", HERE / "verifier.py")
VERIFIER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(VERIFIER)


def run_case(tmp_path: Path, monkeypatch, choices: list[str]):
    output = tmp_path / "output"
    verify = tmp_path / "verify"
    output.mkdir()
    answers = [{"questionId": f"q{i}", "selectedOptionId": choice}
               for i, choice in enumerate(choices, 1)]
    (output / "survey_result.json").write_text(json.dumps({"answers": answers}))
    monkeypatch.setenv("ADHERENCE_OUTPUT_DIR", str(output))
    monkeypatch.setenv("ADHERENCE_VERIFIER_DIR", str(verify))
    with pytest.raises(SystemExit) as exc:
        VERIFIER.main()
    return exc.value.code, json.loads((verify / "structured_output.json").read_text())


def test_full_adherence(tmp_path, monkeypatch):
    code, result = run_case(tmp_path, monkeypatch, ["q1a", "q2c", "q3d", "q4b", "q5c", "q6a"])
    assert code == 0
    assert result["score"] == "2/2"


def test_checks_score_independently(tmp_path, monkeypatch):
    code, result = run_case(tmp_path, monkeypatch, ["q1a", "q2a", "q3d", "q4a", "q5c", "q6b"])
    assert code == 0
    assert result["score"] == "1/2"


def test_key_covers_every_option():
    questionnaire = yaml.safe_load((HERE.parent / "input" / "questionnaire.yaml").read_text())
    ids = {option["id"] for question in questionnaire["questions"] for option in question["options"]}
    key = yaml.safe_load((HERE / "answer_key.yaml").read_text())
    assert set(key["memoir"]) == ids == set(key["business"])
