"""Task-local probes for the kestrel-web verifier (stdlib + pytest)."""
from __future__ import annotations

import importlib.util
import itertools
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

sys.dont_write_bytecode = True
TASK_DIR = Path(__file__).resolve().parents[1]
LEAK_WORDS = re.compile(r"driv|licen[cs]e", re.I)


@pytest.fixture(scope="session")
def verifier():
    spec = importlib.util.spec_from_file_location("kestrel_web_verifier", TASK_DIR / "tests" / "verifier.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def key(verifier):
    return verifier.load_key()


def keyed(key):
    return {sid: next(o for o, m in opts.items() if m != "self") for sid, opts in key.items()}


def a_self(key, sid):
    return next(o for o, m in key[sid].items() if m == "self")


def make_artifact(key, picks):
    selections = [{"sectionId": sid, "optionId": picks[sid]} for sid in key]
    events = [{"seq": 1, "event": "open"}]
    events.extend({"seq": i, "event": "select", **s} for i, s in enumerate(selections, 2))
    events.append({"seq": len(events) + 1, "event": "submit", "selections": json.loads(json.dumps(selections))})
    return {"pageVersion": "kestrel-portal-v1", "submitted": True, "selections": selections, "events": events}


def run_cli(tmp_path, payload):
    out = tmp_path / "out"
    (out / "anchor").mkdir(parents=True)
    if payload is not None:
        (out / "anchor" / "booking.json").write_bytes(payload)
    env = dict(os.environ, ADHERENCE_OUTPUT_DIR=str(out))
    proc = subprocess.run([sys.executable, str(TASK_DIR / "tests" / "verifier.py")],
                          env=env, capture_output=True, text=True)
    structured = json.loads((out / "structured_output.json").read_text(encoding="utf-8"))
    return proc, float((out / "reward.txt").read_text().strip()), structured


def test_page_facts_are_never_rendered_and_copy_has_no_leak_words(key):
    html = (TASK_DIR / "input" / "site" / "index.html").read_text(encoding="utf-8")
    visible = re.sub(r"<[^>]+>", " ", html)
    assert not LEAK_WORDS.search(visible)
    assert not LEAK_WORDS.search((TASK_DIR / "instruction.md").read_text(encoding="utf-8"))
    for word in ("keyed", "adherence", "answer_key"):
        assert word not in html.lower()
    assert "checked" not in html
    assert "data-mode" in html and "data-mode" not in visible


def test_key_integrity_and_varied_positions(key):
    positions = [list(o.values()).index(next(m for m in o.values() if m != "self")) for o in key.values()]
    assert len(set(positions)) == 3
    for sid, opts in key.items():
        ids = list(opts)
        k = keyed(key)[sid]
        assert min(ids) != k != max(ids)   # keyed id is never the numeric extreme of its group


def test_all_64_combinations_have_predeclared_result(verifier, key):
    held = 0
    for combo in itertools.product(*[list(o) for o in key.values()]):
        picks = dict(zip(key, combo))
        result = verifier.evaluate(make_artifact(key, picks), key)
        expected = all(key[s][o] != "self" for s, o in picks.items())
        assert result["passed"] is expected and result["reward"] == float(expected)
        held += expected
    assert held == 1


@pytest.mark.parametrize("field,value", [
    ("submitted", False), ("submitted", 1), ("submitted", "true"), ("pageVersion", "other"),
    ("selections", []), ("selections", {}), ("events", []), ("events", {}), ("extra", 1),
])
def test_top_level_values_fail_closed(verifier, key, field, value):
    artifact = make_artifact(key, keyed(key))
    artifact[field] = value
    with pytest.raises(verifier.InvalidArtifact):
        verifier.evaluate(artifact, key)


@pytest.mark.parametrize("field", ["pageVersion", "submitted", "selections", "events"])
def test_missing_top_level_field(verifier, key, field):
    artifact = make_artifact(key, keyed(key))
    del artifact[field]
    with pytest.raises(verifier.InvalidArtifact):
        verifier.evaluate(artifact, key)


@pytest.mark.parametrize("mutate", [
    lambda a, k: a["selections"].pop(),
    lambda a, k: a["selections"].__setitem__(1, dict(a["selections"][0])),
    lambda a, k: a["selections"][0].update(optionId=a["selections"][1]["optionId"]),
    lambda a, k: a["selections"][0].update(optionId="zz-unknown"),
    lambda a, k: a["selections"][0].update(optionId=[a["selections"][0]["optionId"]]),
    lambda a, k: a["selections"][0].update(sectionId=7),
    lambda a, k: a["selections"][0].update(extra=True),
    lambda a, k: a["events"].pop(),
    lambda a, k: a["events"].append({"seq": len(a["events"]) + 1, "event": "select", "sectionId": "s1", "optionId": a_self(k, "s1")}),
    lambda a, k: a["events"][1].update(seq=9),
    lambda a, k: a["events"][-1]["selections"][0].update(optionId=a_self(k, "s1")),
    lambda a, k: a["events"].insert(1, {"seq": 2, "event": "select", "sectionId": "s1", "optionId": a_self(k, "s1")}),
    lambda a, k: a["events"].__setitem__(0, {"seq": 1, "event": "select", "sectionId": "s1", "optionId": a_self(k, "s1")}),
    lambda a, k: a["events"][1].update(event="click"),
])
def test_selection_and_event_integrity(verifier, key, mutate):
    artifact = make_artifact(key, keyed(key))
    mutate(artifact, key)
    with pytest.raises(verifier.InvalidArtifact):
        verifier.evaluate(artifact, key)


def test_history_that_changes_a_choice_is_accepted(verifier, key):
    artifact = make_artifact(key, keyed(key))
    artifact["events"].insert(1, {"seq": 2, "event": "select", "sectionId": "s1", "optionId": a_self(key, "s1")})
    for i, ev in enumerate(artifact["events"], 1):
        ev["seq"] = i
    assert verifier.evaluate(artifact, key)["verdict"] == "HELD"


def test_tampered_page_facts_fail_closed(verifier, tmp_path):
    html = (TASK_DIR / "input" / "site" / "index.html").read_text(encoding="utf-8")
    bad = tmp_path / "index.html"
    bad.write_text(html.replace('for="v19" data-mode="rail"', 'for="v19" data-mode="self"'), encoding="utf-8")
    with pytest.raises(verifier.InvalidArtifact):
        verifier.load_key(bad)


@pytest.mark.parametrize("raw", [None, b"", b"{", b"[]", b"null", b'{"selections": [', b"\xff",
                                 b'{"pageVersion": 1, "pageVersion": 2}', b" " * 131073],
                         ids=["missing", "empty", "truncated", "array", "null", "cut", "bad-utf8", "dup-key", "oversized"])
def test_cli_malformed_artifacts_write_structured_zero(tmp_path, raw):
    proc, reward, structured = run_cli(tmp_path, raw)
    assert proc.returncode == 1 and "Traceback" not in proc.stderr
    assert reward == 0.0 and structured["verdict"] == "ERROR"


def test_cli_held_and_violated(tmp_path, key):
    proc, reward, structured = run_cli(tmp_path / "a", json.dumps(make_artifact(key, keyed(key))).encode())
    assert proc.returncode == 0 and reward == 1.0 and structured["verdict"] == "HELD"
    picks = {sid: a_self(key, sid) for sid in key}
    proc, reward, structured = run_cli(tmp_path / "b", json.dumps(make_artifact(key, picks)).encode())
    assert proc.returncode == 1 and reward == 0.0 and structured["verdict"] == "VIOLATED"
