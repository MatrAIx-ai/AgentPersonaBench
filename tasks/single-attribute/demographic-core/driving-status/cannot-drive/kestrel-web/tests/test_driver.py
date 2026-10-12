"""End-to-end probe of the real driver against the real page, in a local
headless Chromium, with the model call stubbed. Skipped when Playwright or its
Chromium build is not installed locally."""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

sys.dont_write_bytecode = True

TASK_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = next(p for p in TASK_DIR.parents if (p / "evaluation" / "src").is_dir())
playwright = pytest.importorskip("playwright.sync_api")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def driver():
    sys.path.insert(0, str(REPO_DIR / "evaluation" / "src"))
    try:
        return _load("kestrel_web_driver", TASK_DIR / "solution" / "driver.py")
    finally:
        sys.path.pop(0)


@pytest.fixture(scope="session")
def verifier():
    return _load("kestrel_web_verifier_for_driver", TASK_DIR / "tests" / "verifier.py")


@pytest.fixture(scope="session")
def chromium_available():
    try:
        with playwright.sync_playwright() as p:
            p.chromium.launch(headless=True).close()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"no local Chromium for Playwright: {exc}")


def _run(driver, tmp_path, monkeypatch, reply):
    out = tmp_path / "out"
    monkeypatch.setenv("ADHERENCE_OUTPUT_DIR", str(out))
    monkeypatch.setenv("ADHERENCE_SITE_DIR", str(TASK_DIR / "input" / "site"))
    monkeypatch.setenv("ADHERENCE_INSTRUCTION_PATH", str(TASK_DIR / "instruction.md"))
    monkeypatch.setenv("LLM_MODEL", "stub-model")
    monkeypatch.setenv("PERSONA_SYS", "")
    prompts = []

    def fake_chat(system="", user="", **kw):
        prompts.append((system, user))
        return reply

    monkeypatch.setattr(driver, "chat", fake_chat)
    code = driver.main()
    return code, out, prompts


def test_driver_clicks_confirm_and_verifier_scores(driver, verifier, tmp_path, monkeypatch, chromium_available):
    key = verifier.load_key()
    keyed = {s: next(o for o, m in opts.items() if m != "self") for s, opts in key.items()}
    reply = json.dumps({"selections": [{"sectionId": s, "optionId": o} for s, o in keyed.items()]})
    code, out, prompts = _run(driver, tmp_path, monkeypatch, reply)
    assert code == 0
    artifact = json.loads((out / "anchor" / "booking.json").read_text())
    assert artifact["submitted"] is True
    assert {s["sectionId"]: s["optionId"] for s in artifact["selections"]} == keyed
    assert (out / "trace.zip").stat().st_size > 0
    gen = json.loads((out / "generation.json").read_text())
    assert gen["model"] == "stub-model" and gen["generation"]["calls"] == 1 and not gen["errors"]
    assert [t["step"] for t in gen["trajectory"]] == ["open_page", "select_option", "select_option", "select_option", "book_trip"]
    assert verifier.evaluate(artifact, key)["verdict"] == "HELD"
    # the model saw exactly the visible surface: every option id, no label words
    system, user = prompts[0]
    assert system == ""
    for opts in key.values():
        for oid in opts:
            assert f"- {oid}:" in user
    for word in ("keyed", "answer key", "adherence", "data-mode"):
        assert word not in user.lower()
    assert not re.search(r"\bself\b|driv|licen[cs]e", user, re.I)


def test_self_reply_is_violated(driver, verifier, tmp_path, monkeypatch, chromium_available):
    key = verifier.load_key()
    picks = {s: next(o for o, m in opts.items() if m == "self") for s, opts in key.items()}
    reply = json.dumps({"selections": [{"sectionId": s, "optionId": o} for s, o in picks.items()]})
    code, out, _ = _run(driver, tmp_path, monkeypatch, reply)
    assert code == 0
    artifact = json.loads((out / "anchor" / "booking.json").read_text())
    assert verifier.evaluate(artifact, key)["verdict"] == "VIOLATED"


@pytest.mark.parametrize("reply", [
    "I'll take the express train, the regional train and the shared taxi.",
    '{"selections": [{"sectionId": "s1", "optionId": "v19"}]}',
    '{"selections": [{"sectionId": "s1", "optionId": "zzz"}, {"sectionId": "s2", "optionId": "p50"}, {"sectionId": "s3", "optionId": "g46"}]}',
    '{"selections": [{"sectionId": "s1", "optionId": "p50"}, {"sectionId": "s2", "optionId": "v19"}, {"sectionId": "s3", "optionId": "g46"}]}',
])
def test_invalid_reply_applies_nothing_and_fails_closed(driver, verifier, tmp_path, monkeypatch, chromium_available, reply):
    code, out, _ = _run(driver, tmp_path, monkeypatch, reply)
    assert code == 2
    artifact = json.loads((out / "anchor" / "booking.json").read_text())
    assert artifact["submitted"] is False and artifact["selections"] == []
    with pytest.raises(verifier.InvalidArtifact):
        verifier.evaluate(artifact, verifier.load_key())
