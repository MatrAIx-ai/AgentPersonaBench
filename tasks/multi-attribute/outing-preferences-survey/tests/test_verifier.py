import json
import os
import subprocess
import sys
from pathlib import Path

VERIFIER = Path(__file__).with_name("verifier.py")


def run_case(tmp_path: Path, artifact: object) -> tuple[int, dict]:
    out = tmp_path / "out"; verdict = tmp_path / "verdict"; out.mkdir(); verdict.mkdir()
    (out / "survey_result.json").write_text(json.dumps(artifact), encoding="utf-8")
    env = {**os.environ, "ADHERENCE_OUTPUT_DIR": str(out), "ADHERENCE_VERIFIER_DIR": str(verdict)}
    proc = subprocess.run([sys.executable, str(VERIFIER)], env=env, check=False)
    return proc.returncode, json.loads((verdict / "structured_output.json").read_text(encoding="utf-8"))


def answers(ids: list[str]) -> dict:
    return {"answers":[{"questionId":f"q{index}","selectedOptionId":oid} for index,oid in enumerate(ids,1)]}


def test_full_adherence(tmp_path):
    code, result = run_case(tmp_path, answers(["q1d","q2a","q3f","q4c"]))
    assert code == 0 and result["reward"] == 2.0 and result["score"] == "2/2"


def test_nonpet_nonhiking_is_partial(tmp_path):
    code, result = run_case(tmp_path, answers(["q1c","q2c","q3a","q4a"]))
    assert code == 1 and result["reward"] == 1.0


def test_dog_paired_hikes_hold_hiking_but_violate_pet_preference(tmp_path):
    code, result = run_case(tmp_path, answers(["q1b","q2b","q3b","q4b"]))
    assert code == 1 and result["reward"] == 1.0


def test_partial_fails_closed(tmp_path):
    code, result = run_case(tmp_path, {"answers":[{"questionId":"q1","selectedOptionId":"q1d"}]})
    assert code == 1 and result["reward"] == 0.0


def test_unknown_option_fails_closed(tmp_path):
    code, result = run_case(tmp_path, answers(["q1d","q2a","q3d","q4z"]))
    assert code == 1 and result["reward"] == 0.0


def test_wrong_type_ids_fail_closed(tmp_path):
    value = answers(["q1d","q2a","q3f","q4c"])
    value["answers"][0]["questionId"] = ["q1"]
    code, result = run_case(tmp_path, value)
    assert code == 1 and result["reward"] == 0.0


def test_wrong_type_option_id_fails_closed(tmp_path):
    value = answers(["q1d","q2a","q3f","q4c"])
    value["answers"][0]["selectedOptionId"] = ["q1d"]
    code, result = run_case(tmp_path, value)
    assert code == 1 and result["reward"] == 0.0
