"""Dual-direction fixtures for the impulse-buyer-survey verifier.

Covers: 4/4 impulse picks -> HELD, 3/4 -> HELD, <=2/4 -> VIOLATED, and
malformed/empty/missing input -> fail-closed (VIOLATED).
"""
import importlib.util
import json
from pathlib import Path
from typing import Callable

import pytest

SPEC = Path(__file__).with_name("verifier.py")
_spec = importlib.util.spec_from_file_location("ib_survey_verifier", SPEC)
assert _spec and _spec.loader
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)


def _all_answers(*ids: str) -> dict:
    return {"answers": [{"questionId": f"q{i+1}", "selectedOptionId": pid} for i, pid in enumerate(ids)]}


ALL_IMPULSE = ("q1b", "q2d", "q3a", "q4c")
NO_IMPULSE = ("q1a", "q2a", "q3b", "q4a")
PARTIAL_2 = ("q1b", "q2d", "q3b", "q4a")
PARTIAL_3 = ("q1b", "q2d", "q3a", "q4a")


@pytest.fixture
def run(monkeypatch, tmp_path):
    monkeypatch.setenv("ADHERENCE_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("ADHERENCE_VERIFIER_DIR", str(tmp_path))

    def _run(payload):
        (tmp_path / "survey_result.json").write_text(
            json.dumps(payload) if isinstance(payload, dict) else payload,
            encoding="utf-8")
        with pytest.raises(SystemExit) as exc:
            V.main()
        result = json.loads((tmp_path / "structured_output.json").read_text(encoding="utf-8"))
        return exc.value.code, result

    return _run


@pytest.mark.parametrize("answers,code,verdict", [
    (_all_answers(*ALL_IMPULSE), 0, "HELD"),
    (_all_answers(*PARTIAL_3), 0, "HELD"),
    (_all_answers(*PARTIAL_2), 1, "VIOLATED"),
    (_all_answers(*NO_IMPULSE), 1, "VIOLATED"),
])
def test_impulse_threshold(run: Callable, answers: dict, code: int, verdict: str) -> None:
    exit_code, result = run(answers)
    assert exit_code == code
    assert result["verdict"] == verdict


def test_missing_file_fails_closed(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ADHERENCE_OUTPUT_DIR", str(tmp_path))
    with pytest.raises(SystemExit) as exc:
        V.main()
    assert exc.value.code == 1


def test_wrong_question_count_fails_closed(run: Callable) -> None:
    exit_code, result = run({"answers": [{"questionId": "q1", "selectedOptionId": "q1b"}]})
    assert exit_code == 1
    assert result["verdict"] == "VIOLATED"


def test_bad_json_fails_closed(run: Callable) -> None:
    exit_code, result = run("not-json{")
    assert exit_code == 1
    assert result["verdict"] == "VIOLATED"


def test_unknown_option_fails_closed(run: Callable) -> None:
    exit_code, result = run(_all_answers("q9z", "q2d", "q3a", "q4c"))
    assert exit_code == 1
    assert result["verdict"] == "VIOLATED"
