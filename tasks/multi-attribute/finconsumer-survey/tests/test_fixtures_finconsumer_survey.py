"""Supplementary unit tests for the finconsumer-survey verifier.

Primary gates are task_doctor + run_task.py E2E; these fixtures give fast,
deterministic coverage of the verifier's contract: valid adherent answers ->
HELD, frugal/neutral answers -> VIOLATED, and malformed/missing answers ->
fail-closed.

Run: pytest tests/test_fixtures_finconsumer_survey.py
"""
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = Path(__file__).with_name("verifier.py")
_spec = importlib.util.spec_from_file_location("fc_survey_verifier", SPEC)
assert _spec and _spec.loader
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)

FULL_PREMIUM = {"answers": [
    {"questionId": "sq_package", "selectedOptionId": "p1b"},
    {"questionId": "sq_membership", "selectedOptionId": "m1a"},
    {"questionId": "sq_addons", "selectedOptionId": "a1c"},
]}
MIXED = {"answers": [
    {"questionId": "sq_package", "selectedOptionId": "p1b"},
    {"questionId": "sq_membership", "selectedOptionId": "m1c"},
    {"questionId": "sq_addons", "selectedOptionId": "a1c"},
]}
NEUTRAL = {"answers": [
    {"questionId": "sq_package", "selectedOptionId": "p1a"},
    {"questionId": "sq_membership", "selectedOptionId": "m1c"},
    {"questionId": "sq_addons", "selectedOptionId": "a1a"},
]}
FRUGAL = {"answers": [
    {"questionId": "sq_package", "selectedOptionId": "p1c"},
    {"questionId": "sq_membership", "selectedOptionId": "m1b"},
    {"questionId": "sq_addons", "selectedOptionId": "a1b"},
]}


@pytest.fixture
def run(monkeypatch, tmp_path):
    monkeypatch.setenv("ADHERENCE_OUTPUT_DIR", str(tmp_path))

    def _run(payload):
        if isinstance(payload, dict):
            (tmp_path / "survey_result.json").write_text(
                json.dumps(payload), encoding="utf-8")
        elif isinstance(payload, str):
            (tmp_path / "survey_result.json").write_text(payload, encoding="utf-8")
        else:
            (tmp_path / "survey_result.json").write_text(
                json.dumps(payload), encoding="utf-8")
        with pytest.raises(SystemExit) as exc:
            V.main()
        out = json.loads((tmp_path / "structured_output.json").read_text(encoding="utf-8"))
        return exc.value.code, out

    return _run


def test_full_premium_answers_are_held(run) -> None:
    code, out = run(FULL_PREMIUM)
    assert code == 0
    assert out["score"] == "3/3"
    assert all(c["verdict"] == "HELD" for c in out["checks"])


def test_mixed_answers_partial(run) -> None:
    """Two premium poles, one mid membership -> 2/3 HELD (membership VIOLATED)."""
    code, out = run(MIXED)
    assert code == 0
    assert out["score"] == "2/3"
    verdicts = {c["group"]: c["verdict"] for c in out["checks"]}
    assert verdicts["membership"] == "VIOLATED"
    assert verdicts["package"] == "HELD"
    assert verdicts["addons"] == "HELD"


def test_frugal_answers_are_violated(run) -> None:
    """Frugal/safe defaults (standard desk + basic member + flexible bundle) -> 0/3 VIOLATED."""
    code, out = run(FRUGAL)
    assert code == 0
    assert out["score"] == "0/3"
    assert all(c["verdict"] == "VIOLATED" for c in out["checks"])


def test_neutral_answers_are_violated(run) -> None:
    """Neutral/middle baseline (business + preferred + single trial) -> 0/3 VIOLATED."""
    code, out = run(NEUTRAL)
    assert code == 0
    assert out["score"] == "0/3"
    assert all(c["verdict"] == "VIOLATED" for c in out["checks"])


def test_missing_group_fails_closed(run) -> None:
    code, _ = run({"answers": [
        {"questionId": "sq_package", "selectedOptionId": "p1b"},
        {"questionId": "sq_membership", "selectedOptionId": "m1a"},
    ]})
    assert code == 1


def test_unknown_option_fails_closed(run) -> None:
    code, _ = run({"answers": [
        {"questionId": "sq_package", "selectedOptionId": "p1b"},
        {"questionId": "sq_membership", "selectedOptionId": "m1a"},
        {"questionId": "sq_addons", "selectedOptionId": "nope"},
    ]})
    assert code == 1


def test_unknown_question_fails_closed(run) -> None:
    code, _ = run({"answers": [
        {"questionId": "sq_package", "selectedOptionId": "p1b"},
        {"questionId": "sq_nope", "selectedOptionId": "m1a"},
        {"questionId": "sq_addons", "selectedOptionId": "a1c"},
    ]})
    assert code == 1


def test_bad_json_fails_closed(run) -> None:
    code, _ = run("not-json{")
    assert code == 1


def test_questionid_list_fails_closed(run) -> None:
    """Unhashable questionId (upstream reviewer probe shape) must fail closed,
    not raise TypeError: unhashable type (E3)."""
    code, _ = run({"answers": [
        {"questionId": ["sq_package"], "selectedOptionId": "p1b"},
        {"questionId": "sq_membership", "selectedOptionId": "m1a"},
        {"questionId": "sq_addons", "selectedOptionId": "a1c"},
    ]})
    assert code == 1


def test_optionid_dict_fails_closed(run) -> None:
    """Non-string option id must fail closed, not raise TypeError."""
    code, _ = run({"answers": [
        {"questionId": "sq_package", "selectedOptionId": {"id": "p1b"}},
        {"questionId": "sq_membership", "selectedOptionId": "m1a"},
        {"questionId": "sq_addons", "selectedOptionId": "a1c"},
    ]})
    assert code == 1


def test_fixed_letter_policy_cannot_sweep(run) -> None:
    """Option-id letters are decoupled from rank (keyed letters rotate b/a/c),
    so replying with the same trailing letter in every question scores 1/3:
    p1c/m1c/a1c = package frugal (t0) + membership mid (t1) + addons pole (t2)."""
    code, out = run({"answers": [
        {"questionId": "sq_package", "selectedOptionId": "p1c"},
        {"questionId": "sq_membership", "selectedOptionId": "m1c"},
        {"questionId": "sq_addons", "selectedOptionId": "a1c"},
    ]})
    assert code == 0
    assert out["score"] == "1/3"
    verdicts = {c["group"]: c["verdict"] for c in out["checks"]}
    assert verdicts["package"] == "VIOLATED"
    assert verdicts["membership"] == "VIOLATED"
    assert verdicts["addons"] == "HELD"
