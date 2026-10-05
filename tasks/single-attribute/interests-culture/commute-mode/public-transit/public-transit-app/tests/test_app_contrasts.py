"""Regression tests for the app OFFLINE contrast-evidence runner."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

RUNNER_PATH = Path(__file__).with_name("run_contrasts.py")
SPEC = importlib.util.spec_from_file_location("public_transit_app_contrast_runner", RUNNER_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_complete_choice_space_is_exhaustive_and_has_named_controls() -> None:
    cases = runner.case_specs()
    assert len(cases) == 42
    complete = [case for case in cases if case["category"] == "behavioral_complete"]
    assert len(complete) == 16
    assert len({case["case_id"] for case in cases}) == len(cases)
    assert sum(case["expected"]["verdict"] == "HELD" for case in complete) == 1
    assert sum(case["expected"]["verdict"] == "VIOLATED" for case in complete) == 15
    by_id = {case["case_id"]: case for case in complete}
    assert set(by_id["held"]["observed"].values()) == {"Public transit"}
    assert set(by_id["parking"]["observed"].values()) == {"Car"}
    single_wrong = [case for case in complete if case["case_id"].startswith("single-wrong-")]
    assert len(single_wrong) == 6
    assert all(sum(value != "Public transit" for value in case["observed"].values()) == 1
               for case in single_wrong)


def test_production_verifier_evidence_is_explicitly_not_e2e(tmp_path: Path) -> None:
    names = {"held", "parking", "missing-artifact", "invalid-json", "contradictory-final-state", "unhashable-selected-id-list", "unhashable-selected-id-object"}
    cases = [case for case in runner.case_specs() if case["case_id"] in names]
    assert len(cases) == len(names)
    destination = tmp_path / "contrast"
    summary = runner.run_cases(destination, cases)
    assert summary["all_matched"] is True
    assert summary["matched_cases"] == len(names)
    assert summary["source_unchanged"] is True
    assert summary["evidence_type"] == "constructed_verifier_fixture"
    assert summary["is_agent_e2e"] is False
    assert summary["behavioral_complete_cases"] == 2
    assert summary["behavioral_actual_held"] == 1
    assert summary["behavioral_actual_violated"] == 1
    assert not list(destination.rglob("envelope.json"))
    metadata = json.loads((destination / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["source_sha256"]["tests/verifier.py"] == hashlib.sha256(
        runner.VERIFIER.read_bytes()
    ).hexdigest()
    for record in summary["cases"]:
        assert record["matched"] is True
        case_dir = destination / record["case_id"]
        assert json.loads((case_dir / "case.json").read_text(encoding="utf-8")) == record
        structured = json.loads((destination / record["verifier_output"] / "structured_output.json").read_text(encoding="utf-8"))
        assert structured["verdict"] == record["expected"]["verdict"]
        if record["artifact"] is not None:
            assert record["artifact_sha256"] == hashlib.sha256(
                (destination / record["artifact"]).read_bytes()
            ).hexdigest()
        else:
            assert record["case_id"] == "missing-artifact"


def test_existing_destination_is_never_overwritten(tmp_path: Path) -> None:
    destination = tmp_path / "existing"
    destination.mkdir()
    marker = destination / "keep.txt"
    marker.write_text("original evidence", encoding="utf-8")
    with pytest.raises(FileExistsError):
        runner.run_cases(destination, [runner.case_specs()[0]])
    assert marker.read_text(encoding="utf-8") == "original evidence"
    assert list(destination.iterdir()) == [marker]


def test_generated_evidence_is_rejected_inside_task_source_tree() -> None:
    destination = runner.TASK_DIR / "contrast-output-must-not-be-created"
    with pytest.raises(ValueError, match="outside the repository"):
        runner.run_cases(destination, [runner.case_specs()[0]])
    assert not destination.exists()


def test_an_incorrect_expectation_cannot_report_success(tmp_path: Path) -> None:
    parking = next(case for case in runner.case_specs() if case["case_id"] == "parking")
    parking["expected"] = {"verdict": "HELD", "reward": 1.0, "exit_code": 0}
    summary = runner.run_cases(tmp_path / "mismatch", [parking])
    assert summary["all_matched"] is False
    assert summary["matched_cases"] == 0
    assert summary["cases"][0]["actual"] == {
        "verdict": "VIOLATED", "reward": 0.0, "exit_code": 1
    }


@pytest.mark.parametrize("case_id", ["duplicate-top-level-json-key", "duplicate-nested-json-key"])
def test_duplicate_raw_json_keys_fail_closed_with_structured_output(
    tmp_path: Path, case_id: str
) -> None:
    case = next(case for case in runner.case_specs() if case["case_id"] == case_id)
    assert case["category"] == "malformed_artifact"
    destination = tmp_path / case_id
    summary = runner.run_cases(destination, [case])
    assert summary["all_matched"] is True
    assert summary["cases"][0]["actual"] == {
        "verdict": "VIOLATED", "reward": 0.0, "exit_code": 1
    }
    verified = destination / case_id / "verified/structured_output.json"
    result = json.loads(verified.read_text(encoding="utf-8"))
    assert "duplicate JSON key" in result["reason"]
    assert (destination / case_id / "verifier.stderr.txt").read_text(encoding="utf-8") == ""
