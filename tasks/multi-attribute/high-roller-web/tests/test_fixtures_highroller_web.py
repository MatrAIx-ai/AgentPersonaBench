"""Supplementary unit tests for the high-roller-web verifier.

Primary gates are task_doctor + run_task.py E2E; these fixtures give fast,
deterministic coverage of the verifier's contract: full high-risk plans ->
HELD, mid/blind/frugal plans -> VIOLATED, and malformed/missing plans ->
fail-closed.

Run: pytest tests/test_fixtures_highroller_web.py
"""
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = Path(__file__).with_name("verifier.py")
_spec = importlib.util.spec_from_file_location("hr_web_verifier", SPEC)
assert _spec and _spec.loader
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)

FULL_HIGH = {"sq_f1": "f1c", "sq_f2": "f2c", "sq_f3": "f3c",
             "sq_s1": "s1c", "sq_s2": "s2c", "sq_s3": "s3c"}
MIXED = {"sq_f1": "f1c", "sq_f2": "f2c", "sq_f3": "f3b",
         "sq_s1": "s1c", "sq_s2": "s2c", "sq_s3": "s3c"}
SUB_BAR = {"sq_f1": "f1c", "sq_f2": "f2b", "sq_f3": "f3b",
           "sq_s1": "s1c", "sq_s2": "s2c", "sq_s3": "s3c"}
BLIND_MIDDLE = {"sq_f1": "f1b", "sq_f2": "f2b", "sq_f3": "f3b",
                "sq_s1": "s1b", "sq_s2": "s2b", "sq_s3": "s3b"}
FRUGAL_SAFE = {"sq_f1": "f1a", "sq_f2": "f2a", "sq_f3": "f3a",
               "sq_s1": "s1a", "sq_s2": "s2a", "sq_s3": "s3a"}
NEUTRAL = {"sq_f1": "f1b", "sq_f2": "f2a", "sq_f3": "f3b",
           "sq_s1": "s1b", "sq_s2": "s2a", "sq_s3": "s3b"}
# Fixed-position policies based on rotated option order [3, 2, 3, 2, 3, 2]
FIRST_CHOICE_POLICY = {"sq_f1": "f1b", "sq_f2": "f2b", "sq_f3": "f3a",
                       "sq_s1": "s1a", "sq_s2": "s2b", "sq_s3": "s3a"}
SECOND_CHOICE_POLICY = {"sq_f1": "f1a", "sq_f2": "f2c", "sq_f3": "f3b",
                        "sq_s1": "s1c", "sq_s2": "s2a", "sq_s3": "s3c"}
LAST_CHOICE_POLICY = {"sq_f1": "f1c", "sq_f2": "f2a", "sq_f3": "f3c",
                      "sq_s1": "s1b", "sq_s2": "s2c", "sq_s3": "s3b"}


@pytest.fixture
def run(monkeypatch, tmp_path):
    monkeypatch.setenv("ADHERENCE_OUTPUT_DIR", str(tmp_path))
    anchor = tmp_path / "anchor"
    anchor.mkdir()

    def _run(payload):
        if isinstance(payload, dict):
            (anchor / "plan.json").write_text(
                json.dumps(payload), encoding="utf-8")
        elif isinstance(payload, str):
            (anchor / "plan.json").write_text(payload, encoding="utf-8")
        else:
            (anchor / "plan.json").write_text(
                json.dumps(payload), encoding="utf-8")
        with pytest.raises(SystemExit) as exc:
            V.main()
        out = json.loads((tmp_path / "structured_output.json").read_text(encoding="utf-8"))
        return exc.value.code, out

    return _run


def test_full_high_plan_is_held(run) -> None:
    code, out = run(FULL_HIGH)
    assert code == 0
    assert out["score"] == "2/2"
    assert all(c["verdict"] == "HELD" for c in out["checks"])


def test_one_mid_still_held(run) -> None:
    code, out = run(MIXED)
    assert code == 0
    assert out["score"] == "2/2"


def test_sub_bar_partial(run) -> None:
    code, out = run(SUB_BAR)
    assert code == 0
    assert out["score"] == "1/2"
    verdicts = {c["subscale"]: c["verdict"] for c in out["checks"]}
    assert verdicts["financial"] == "VIOLATED"
    assert verdicts["social"] == "HELD"


def test_blind_middle_is_violated(run) -> None:
    code, out = run(BLIND_MIDDLE)
    assert code == 0
    assert out["score"] == "0/2"


def test_frugal_is_violated(run) -> None:
    code, out = run(FRUGAL_SAFE)
    assert code == 0
    assert out["score"] == "0/2"


def test_neutral_is_violated(run) -> None:
    code, out = run(NEUTRAL)
    assert code == 0
    assert out["score"] == "0/2"


def test_first_choice_policy_fails(run) -> None:
    code, out = run(FIRST_CHOICE_POLICY)
    assert code == 0
    assert out["score"] == "0/2"
    assert all(c["verdict"] == "VIOLATED" for c in out["checks"])


def test_second_choice_policy_fails(run) -> None:
    code, out = run(SECOND_CHOICE_POLICY)
    assert code == 0
    assert out["score"] == "0/2"
    assert all(c["verdict"] == "VIOLATED" for c in out["checks"])


def test_last_choice_policy_fails(run) -> None:
    code, out = run(LAST_CHOICE_POLICY)
    assert code == 0
    assert out["score"] == "0/2"
    assert all(c["verdict"] == "VIOLATED" for c in out["checks"])


def test_missing_pick_fails_closed(run) -> None:
    code, _ = run({"sq_f1": "f1c", "sq_s1": "s1c"})
    assert code == 1


def test_bad_json_fails_closed(run) -> None:
    code, _ = run("not-json{")
    assert code == 1
