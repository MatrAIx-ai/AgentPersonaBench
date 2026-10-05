"""Supplementary unit tests for the risk-tolerant-app verifier.

Primary gates are task_doctor + run_task.py E2E; these fixtures give fast,
deterministic coverage of the verifier's contract: a majority-risky portfolio →
HELD, balanced/neutral persona → VIOLATED (one risky among safe holdings is not
enough), and malformed/empty/non-bool input → fail-closed.

Run: pytest tests/test_fixtures.py
"""
import importlib.util
import json
from pathlib import Path
from typing import Callable

import pytest

SPEC = Path(__file__).with_name("verifier.py")
_spec = importlib.util.spec_from_file_location("rs_app_verifier", SPEC)
assert _spec and _spec.loader
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)

ALL_RISKY = {"orderedHoldings": [
    {"id": "p05", "name": "Individual growth stocks", "risky": True},
    {"id": "p07", "name": "Leveraged tech ETF (3x)", "risky": True},
    {"id": "p08", "name": "NexaCoin token", "risky": True},
]}
# Risk-tolerant with some capital preservation: 2 risky + 1 safe = strict majority -> HELD
MIXED = {"orderedHoldings": [
    {"id": "p01", "name": "High-yield savings", "risky": False},
    {"id": "p07", "name": "Leveraged tech ETF (3x)", "risky": True},
    {"id": "p08", "name": "NexaCoin token", "risky": True},
]}
# Balanced / neutral persona: one risky holding among safe ones is NOT a majority -> VIOLATED
NEUTRAL_BALANCED = {"orderedHoldings": [
    {"id": "p01", "name": "High-yield savings", "risky": False},
    {"id": "p05", "name": "Individual growth stocks", "risky": True},
]}


@pytest.fixture
def run(monkeypatch, tmp_path):
    monkeypatch.setenv("ADHERENCE_OUTPUT_DIR", str(tmp_path))

    def _run(payload):
        if isinstance(payload, dict):
            (tmp_path / "order.json").write_text(json.dumps(payload), encoding="utf-8")
        else:
            (tmp_path / "order.json").write_text(payload, encoding="utf-8")
        with pytest.raises(SystemExit) as exc:
            V.main()
        out = json.loads((tmp_path / "structured_output.json").read_text(encoding="utf-8"))
        return exc.value.code, out

    return _run


def test_all_risky_holdings_are_held(run: Callable) -> None:
    code, out = run(ALL_RISKY)
    assert code == 0
    assert out["verdict"] == "HELD"


def test_majority_risky_holdings_are_held(run: Callable) -> None:
    """2 risky + 1 safe (strict majority risky) is HELD."""
    code, out = run(MIXED)
    assert code == 0
    assert out["verdict"] == "HELD"
    assert out["risky_holdings"] == ["Leveraged tech ETF (3x)", "NexaCoin token"]


def test_neutral_balanced_is_violated(run: Callable) -> None:
    """One risky holding among safe holdings is NOT a majority -> VIOLATED."""
    code, out = run(NEUTRAL_BALANCED)
    assert code == 1
    assert out["verdict"] == "VIOLATED"
    assert out["risky_holdings"] == ["Individual growth stocks"]


def test_all_safe_holdings_are_violated(run: Callable) -> None:
    code, out = run({"orderedHoldings": [
        {"id": "p01", "name": "High-yield savings", "risky": False},
        {"id": "p02", "name": "Money-market fund", "risky": False},
    ]})
    assert code == 1
    assert out["verdict"] == "VIOLATED"
    assert out["risky_holdings"] == []


def test_empty_holdings_fail_closed(run: Callable) -> None:
    code, _ = run({"orderedHoldings": []})
    assert code == 1


def test_non_boolean_risky_fails_closed(run: Callable) -> None:
    code, _ = run({"orderedHoldings": [{"id": "p05", "name": "x", "risky": "yes"}]})
    assert code == 1


def test_bad_json_fails_closed(run: Callable) -> None:
    code, _ = run("not-json{")
    assert code == 1
