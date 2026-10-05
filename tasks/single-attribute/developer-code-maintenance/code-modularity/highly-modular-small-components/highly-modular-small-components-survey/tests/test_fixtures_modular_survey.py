"""Supplementary unit tests for the highly-modular-small-components-survey verifier.

Primary gates are task_doctor + run_task.py E2E; these fixtures give fast,
deterministic coverage of the verifier's contract: decomposed small helpers ->
HELD, monoliths/thin splits/oversized helpers -> VIOLATED, and
malformed/missing artifacts -> fail-closed.

Run: pytest tests/test_fixtures_modular_survey.py
"""
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = Path(__file__).with_name("verifier.py")
_spec = importlib.util.spec_from_file_location("md_survey_verifier", SPEC)
assert _spec and _spec.loader
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)


def _fn(name, lines):
    body = "\n".join(f"    _s{i} = {i}" for i in range(max(lines - 2, 1)))
    return f"def {name}():\n    _a = 1\n{body}\n    return _a\n"


ADHERENT = "\n\n".join([
    _fn("validate_transaction", 12),
    _fn("compute_processing_fee", 9),
    _fn("check_velocity_flag", 11),
    _fn("format_ledger_entry", 8),
    _fn("process_transaction_batch", 15),
])

MONOLITH = '''def process_transaction_batch(records, fee_schedule):
    ledger = []
    for r in records:
        if "tx_id" not in r:
            continue
        if "amount" not in r:
            continue
        if "timestamp" not in r:
            continue
        if "currency" not in r:
            continue
        if r["amount"] < 0:
            continue
        currency = r["currency"].upper()
        rate = fee_schedule.get(currency, 0.05)
        fee = r["amount"] * rate + 0.30
        flagged = r["amount"] > 10000
        if flagged:
            status = "review"
        else:
            status = "ok"
        entry = {}
        entry["id"] = r["tx_id"]
        entry["amount"] = r["amount"]
        entry["fee"] = round(fee, 2)
        entry["currency"] = currency
        entry["status"] = status
        ledger.append(entry)
    return ledger
'''

THIN_SPLIT = "\n\n".join([
    _fn("process_transaction_batch", 20),
    _fn("helper", 6),
])

OVERSIZED_ONE = "\n\n".join([
    _fn("validate_transaction", 12),
    _fn("compute_processing_fee", 9),
    _fn("check_velocity_flag", 11),
    _fn("format_ledger_entry", 8),
    "def process_transaction_batch(records, fee_schedule):\n" + "\n".join(
        f"    _step{i} = {i}" for i in range(30)) + "\n    return []\n",
])

CLASS_FOUR_SMALL_METHODS = '''class BatchProcessor:
    """Pipeline with small methods counts: units are units."""

    def validate(self, r):
        return True

    def fee(self, a):
        return a

    def flag(self, r):
        return False

    def run(self, rs):
        return [r for r in rs]
'''


@pytest.fixture
def run(monkeypatch, tmp_path):
    monkeypatch.setenv("ADHERENCE_OUTPUT_DIR", str(tmp_path))
    sol = tmp_path / "solution"
    sol.mkdir()

    def _run(payload):
        if isinstance(payload, dict):
            (sol / "solution.py").write_text(
                json.dumps(payload), encoding="utf-8")
        elif isinstance(payload, str):
            (sol / "solution.py").write_text(payload, encoding="utf-8")
        else:
            (sol / "solution.py").write_text(
                json.dumps(payload), encoding="utf-8")
        with pytest.raises(SystemExit) as exc:
            V.main()
        out = json.loads((tmp_path / "structured_output.json").read_text(encoding="utf-8"))
        return exc.value.code, out

    return _run


def test_decomposed_helpers_are_held(run) -> None:
    """5 helpers, all <=15 lines -> HELD."""
    code, out = run(ADHERENT)
    assert code == 0
    assert out["reward"] == 1.0
    assert out["passed"] is True
    assert out["function_count"] == 5


def test_monolith_is_violated(run) -> None:
    """Single 30-line function -> VIOLATED (both count and span fail)."""
    code, out = run(MONOLITH)
    assert code == 0
    assert out["reward"] == 0.0
    assert out["passed"] is False


def test_thin_split_is_violated(run) -> None:
    """Boundary: only 2 helpers -> VIOLATED."""
    code, out = run(THIN_SPLIT)
    assert code == 0
    assert out["reward"] == 0.0


def test_oversized_helper_is_violated(run) -> None:
    """4+ helpers but one 30-line unit -> VIOLATED with the offender named."""
    code, out = run(OVERSIZED_ONE)
    assert code == 0
    assert out["reward"] == 0.0
    assert "process_transaction_batch" in out["detail"]


def test_class_small_methods_are_held(run) -> None:
    """Documented choice: small methods count as units -> HELD."""
    code, out = run(CLASS_FOUR_SMALL_METHODS)
    assert code == 0
    assert out["reward"] == 1.0
    assert out["passed"] is True


def test_missing_file_fails_closed(run, tmp_path) -> None:
    import shutil
    shutil.rmtree(tmp_path / "solution")
    with pytest.raises(SystemExit) as exc:
        V.main()
    assert exc.value.code == 1


def test_bad_syntax_fails_closed(run) -> None:
    code, _ = run("def broken(:\n  pass\n")
    assert code == 1


def test_no_functions_fails_closed(run) -> None:
    code, _ = run("X = 1\nY = 2\n")
    assert code == 1
