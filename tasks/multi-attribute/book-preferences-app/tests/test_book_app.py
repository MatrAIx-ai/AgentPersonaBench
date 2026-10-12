from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("book_app_verifier", HERE / "verifier.py")
VERIFIER = importlib.util.module_from_spec(SPEC); assert SPEC.loader; SPEC.loader.exec_module(VERIFIER)


def run_case(tmp_path, monkeypatch, ids, submitted=True):
    output = tmp_path / "output"; verify = tmp_path / "verify"; output.mkdir()
    (output / "loan.json").write_text(json.dumps({"submitted": submitted, "selectedBookIds": ids}))
    monkeypatch.setenv("ADHERENCE_OUTPUT_DIR", str(output)); monkeypatch.setenv("ADHERENCE_VERIFIER_DIR", str(verify))
    with pytest.raises(SystemExit) as exc: VERIFIER.main()
    return exc.value.code, json.loads((verify / "structured_output.json").read_text())


def test_full_adherence(tmp_path, monkeypatch):
    code, result = run_case(tmp_path, monkeypatch, ["b08", "b14"])
    assert code == 0 and result["score"] == "2/2"


def test_independent_scoring(tmp_path, monkeypatch):
    code, result = run_case(tmp_path, monkeypatch, ["b08", "b11"])
    assert code == 0 and result["score"] == "1/2"


def test_rejects_unsubmitted(tmp_path, monkeypatch):
    code, result = run_case(tmp_path, monkeypatch, ["b08", "b14"], submitted=False)
    assert code == 1 and result["verdict"] == "ERROR"


def test_rejects_book_removed_from_curated_catalog(tmp_path, monkeypatch):
    code, result = run_case(tmp_path, monkeypatch, ["b02", "b14"])
    assert code == 1 and result["verdict"] == "ERROR"


def test_catalog_has_five_books_per_display():
    assert len(VERIFIER.KNOWN) == 10
    assert list(VERIFIER.DISPLAYS.values()).count("A") == 5
    assert list(VERIFIER.DISPLAYS.values()).count("B") == 5
