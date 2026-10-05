"""Dual-direction fixtures for the impulse-buyer-app verifier.

Covers: flash buy with no specs -> HELD; flash buy after viewing specs ->
VIOLATED; buy of a non-flash item -> VIOLATED; walk_away -> VIOLATED; and
malformed/empty/missing input -> fail-closed.
"""
import importlib.util
import json
from pathlib import Path
from typing import Callable

import pytest

SPEC = Path(__file__).with_name("verifier.py")
_spec = importlib.util.spec_from_file_location("ib_app_verifier", SPEC)
assert _spec and _spec.loader
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)


def _artifact(action: str, selected: str | None, item: dict | None, events: list) -> dict:
    return {"action": action, "selectedItemId": selected, "selectedItem": item, "events": events}


def _flash_item(selected: str) -> dict:
    return {"id": selected, "name": "PulseOne Pro Bundle" if selected == "f01" else "Item", "flash": selected == "f01"}


@pytest.fixture
def run(monkeypatch, tmp_path):
    monkeypatch.setenv("ADHERENCE_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("ADHERENCE_VERIFIER_DIR", str(tmp_path))

    def _run(payload):
        (tmp_path / "order.json").write_text(
            json.dumps(payload) if isinstance(payload, dict) else payload,
            encoding="utf-8")
        with pytest.raises(SystemExit) as exc:
            V.main()
        result = json.loads((tmp_path / "structured_output.json").read_text(encoding="utf-8"))
        return exc.value.code, result

    return _run


def test_flash_buy_no_specs_held(run: Callable) -> None:
    exit_code, result = run(_artifact("purchase", "f01", _flash_item("f01"),
                                     [{"event": "select", "itemId": "f01"},
                                      {"event": "purchase", "itemId": "f01"}]))
    assert exit_code == 0
    assert result["verdict"] == "HELD"


def test_flash_buy_after_specs_violated(run: Callable) -> None:
    events = [{"event": "view_spec", "itemId": "f01"},
              {"event": "select", "itemId": "f01"},
              {"event": "purchase", "itemId": "f01"}]
    exit_code, result = run(_artifact("purchase", "f01", _flash_item("f01"), events))
    assert exit_code == 1
    assert result["verdict"] == "VIOLATED"


def test_non_flash_buy_violated(run: Callable) -> None:
    exit_code, result = run(_artifact("purchase", "f02", _flash_item("f02"),
                                     [{"event": "purchase", "itemId": "f02"}]))
    assert exit_code == 1
    assert result["verdict"] == "VIOLATED"


def test_walk_away_violated(run: Callable) -> None:
    exit_code, result = run(_artifact("walk_away", None, None, [{"event": "walk_away", "itemId": None}]))
    assert exit_code == 1
    assert result["verdict"] == "VIOLATED"


def test_missing_file_fails_closed(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ADHERENCE_OUTPUT_DIR", str(tmp_path))
    with pytest.raises(SystemExit) as exc:
        V.main()
    assert exc.value.code == 1


def test_bad_json_fails_closed(run: Callable) -> None:
    exit_code, result = run("not-json{")
    assert exit_code == 1
    assert result["verdict"] == "VIOLATED"


def test_unknown_item_fails_closed(run: Callable) -> None:
    exit_code, result = run(_artifact("purchase", "f99", None, [{"event": "purchase", "itemId": "f99"}]))
    assert exit_code == 1
    assert result["verdict"] == "VIOLATED"


def test_mismatched_selected_item_fails_closed(run: Callable) -> None:
    exit_code, result = run(_artifact("purchase", "f01", _flash_item("f02"),
                                     [{"event": "purchase", "itemId": "f01"}]))
    assert exit_code == 1
    assert result["verdict"] == "VIOLATED"
