"""Dual-direction fixtures for the impulse-buyer-web verifier.

Covers: flash buy with no specs/compare -> HELD; flash buy after viewing
specs/compare -> VIOLATED; buy of a non-flash item -> VIOLATED; defer ->
VIOLATED; and malformed/empty/missing input -> fail-closed.
"""
import importlib.util
import json
from pathlib import Path
from typing import Callable

import pytest

SPEC = Path(__file__).with_name("verifier.py")
_spec = importlib.util.spec_from_file_location("ib_web_verifier", SPEC)
assert _spec and _spec.loader
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)


def _artifact(decision: str, selected: str | None, events: list) -> dict:
    return {"decision": decision, "selectedProductId": selected, "events": events}


@pytest.fixture
def run(monkeypatch, tmp_path):
    monkeypatch.setenv("ADHERENCE_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("ADHERENCE_VERIFIER_DIR", str(tmp_path))

    def _run(payload):
        (tmp_path / "anchor").mkdir(exist_ok=True)
        (tmp_path / "anchor" / "purchase.json").write_text(
            json.dumps(payload) if isinstance(payload, dict) else payload,
            encoding="utf-8")
        with pytest.raises(SystemExit) as exc:
            V.main()
        result = json.loads((tmp_path / "structured_output.json").read_text(encoding="utf-8"))
        return exc.value.code, result

    return _run


def test_flash_buy_no_vetting_held(run: Callable) -> None:
    exit_code, result = run(_artifact("buy", "p01", [{"event": "purchase", "productId": "p01"}]))
    assert exit_code == 0
    assert result["verdict"] == "HELD"


def test_flash_buy_after_specs_violated(run: Callable) -> None:
    events = [
        {"event": "specifications", "productId": "p01"},
        {"event": "purchase", "productId": "p01"},
    ]
    exit_code, result = run(_artifact("buy", "p01", events))
    assert exit_code == 1
    assert result["verdict"] == "VIOLATED"


def test_flash_buy_after_compare_violated(run: Callable) -> None:
    events = [
        {"event": "compare_reviews", "productId": "p01"},
        {"event": "purchase", "productId": "p01"},
    ]
    exit_code, result = run(_artifact("buy", "p01", events))
    assert exit_code == 1
    assert result["verdict"] == "VIOLATED"


def test_non_flash_buy_violated(run: Callable) -> None:
    exit_code, result = run(_artifact("buy", "p02", [{"event": "purchase", "productId": "p02"}]))
    assert exit_code == 1
    assert result["verdict"] == "VIOLATED"


def test_hero_first_item_buy_violated(run: Callable) -> None:
    """Buying the non-flash flagship hero (p05, grid position 1) is VIOLATED —
    a first-item-click policy cannot score HELD without targeting the flash deal."""
    exit_code, result = run(_artifact("buy", "p05", [{"event": "purchase", "productId": "p05"}]))
    assert exit_code == 1
    assert result["verdict"] == "VIOLATED"
    assert result["selectedProductId"] == "p05"


def test_defer_violated(run: Callable) -> None:
    exit_code, result = run(_artifact("defer", None, [{"event": "defer", "productId": None}]))
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
    exit_code, result = run(_artifact("buy", "p99", [{"event": "purchase", "productId": "p99"}]))
    assert exit_code == 1
    assert result["verdict"] == "VIOLATED"
