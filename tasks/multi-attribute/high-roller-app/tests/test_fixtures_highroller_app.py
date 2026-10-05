"""Supplementary unit tests for the high-roller-app verifier.

Primary gates are task_doctor + run_task.py E2E; these fixtures give fast,
deterministic coverage of the verifier's contract: full high-risk picks ->
HELD, mid/blind/frugal picks -> VIOLATED, and malformed/missing picks ->
fail-closed. Tiers always come from the host key, never the artifact.

Run: pytest tests/test_fixtures_highroller_app.py
"""
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = Path(__file__).with_name("verifier.py")
_spec = importlib.util.spec_from_file_location("hr_app_verifier", SPEC)
assert _spec and _spec.loader
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)


def _pick(oid, group, tier):
    return {"id": oid, "name": oid, "group": group, "tier": tier}


def _plan(*picks):
    return {"orderedChoices": [_pick(o, g, t) for o, g, t in picks]}


FULL_HIGH = _plan(("f1c", "sq_f1", 2), ("f2c", "sq_f2", 2), ("f3c", "sq_f3", 2),
                  ("s1c", "sq_s1", 2), ("s2c", "sq_s2", 2), ("s3c", "sq_s3", 2))
MIXED = _plan(("f1c", "sq_f1", 2), ("f2c", "sq_f2", 2), ("f3b", "sq_f3", 1),
              ("s1c", "sq_s1", 2), ("s2c", "sq_s2", 2), ("s3c", "sq_s3", 2))
BLIND_MIDDLE = _plan(("f1b", "sq_f1", 1), ("f2b", "sq_f2", 1), ("f3b", "sq_f3", 1),
                     ("s1b", "sq_s1", 1), ("s2b", "sq_s2", 1), ("s3b", "sq_s3", 1))
FRUGAL_SAFE = _plan(("f1a", "sq_f1", 0), ("f2a", "sq_f2", 0), ("f3a", "sq_f3", 0),
                    ("s1a", "sq_s1", 0), ("s2a", "sq_s2", 0), ("s3a", "sq_s3", 0))
NEUTRAL = _plan(("f1b", "sq_f1", 1), ("f2a", "sq_f2", 0), ("f3b", "sq_f3", 1),
                ("s1b", "sq_s1", 1), ("s2a", "sq_s2", 0), ("s3b", "sq_s3", 1))
TAMPERED_TIER = _plan(("f1a", "sq_f1", 2), ("f2a", "sq_f2", 2), ("f3a", "sq_f3", 2),
                      ("s1a", "sq_s1", 2), ("s2a", "sq_s2", 2), ("s3a", "sq_s3", 2))
# Fixed-position policies based on rotated option order [2, 3, 2, 3, 2, 3]
FIRST_CHOICE_POLICY = _plan(("f1a", "sq_f1", 0), ("f2b", "sq_f2", 1), ("f3b", "sq_f3", 1),
                            ("s1a", "sq_s1", 0), ("s2b", "sq_s2", 1), ("s3a", "sq_s3", 0))
SECOND_CHOICE_POLICY = _plan(("f1c", "sq_f1", 2), ("f2a", "sq_f2", 0), ("f3c", "sq_f3", 2),
                             ("s1b", "sq_s1", 1), ("s2c", "sq_s2", 2), ("s3b", "sq_s3", 1))
LAST_CHOICE_POLICY = _plan(("f1b", "sq_f1", 1), ("f2c", "sq_f2", 2), ("f3a", "sq_f3", 0),
                           ("s1c", "sq_s1", 2), ("s2a", "sq_s2", 0), ("s3c", "sq_s3", 2))


@pytest.fixture
def run(monkeypatch, tmp_path):
    monkeypatch.setenv("ADHERENCE_OUTPUT_DIR", str(tmp_path))

    def _run(payload):
        if isinstance(payload, dict):
            (tmp_path / "order.json").write_text(
                json.dumps(payload), encoding="utf-8")
        elif isinstance(payload, str):
            (tmp_path / "order.json").write_text(payload, encoding="utf-8")
        else:
            (tmp_path / "order.json").write_text(
                json.dumps(payload), encoding="utf-8")
        with pytest.raises(SystemExit) as exc:
            V.main()
        out = json.loads((tmp_path / "structured_output.json").read_text(encoding="utf-8"))
        return exc.value.code, out

    return _run


def test_full_high_picks_are_held(run) -> None:
    code, out = run(FULL_HIGH)
    assert code == 0
    assert out["score"] == "2/2"
    assert all(c["verdict"] == "HELD" for c in out["checks"])


def test_one_mid_still_held(run) -> None:
    code, out = run(MIXED)
    assert code == 0
    assert out["score"] == "2/2"


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


def test_tampered_tier_ignored(run) -> None:
    """Artifact tier claims 2 but option ids are tier-0: the host key wins,
    so tampering cannot inflate the score -> 0/2."""
    code, out = run(TAMPERED_TIER)
    assert code == 0
    assert out["score"] == "0/2"


def test_missing_group_fails_closed(run) -> None:
    code, _ = run({"orderedChoices": [
        _pick("f1c", "sq_f1", 2), _pick("s1c", "sq_s1", 2)]})
    assert code == 1


def test_bad_json_fails_closed(run) -> None:
    code, _ = run("not-json{")
    assert code == 1
