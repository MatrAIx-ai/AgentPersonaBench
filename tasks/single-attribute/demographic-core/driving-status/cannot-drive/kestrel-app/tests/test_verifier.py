"""Task-local probes for the kestrel-app verifier and the app catalog."""
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
    spec = importlib.util.spec_from_file_location("kestrel_app_verifier", TASK_DIR / "tests" / "verifier.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def key(verifier):
    return verifier.load_key()


def make_artifact(key, picks):
    return {"appVersion": "kestrel-itinerary-v1", "submitted": True,
            "selections": [{"sectionId": s, "optionId": picks[s], "name": key[s][picks[s]]["name"]} for s in key]}


def keyed(key):
    return {s: next(o for o, spec in opts.items() if spec["mode"] != "self") for s, opts in key.items()}


def selfs(key):
    return {s: next(o for o, spec in opts.items() if spec["mode"] == "self") for s, opts in key.items()}


def _run_cli(tmp_path, payload):
    out = tmp_path / "out"
    out.mkdir()
    if payload is not None:
        (out / "itinerary.json").write_bytes(payload)
    env = dict(os.environ, ADHERENCE_OUTPUT_DIR=str(out))
    proc = subprocess.run([sys.executable, str(TASK_DIR / "tests" / "verifier.py")],
                          env=env, capture_output=True, text=True)
    structured = json.loads((out / "structured_output.json").read_text(encoding="utf-8"))
    return proc, float((out / "reward.txt").read_text().strip()), structured


def test_app_copies_are_byte_identical():
    assert (TASK_DIR / "input" / "app" / "kestrel.py").read_bytes() == (TASK_DIR / "environment" / "kestrel.py").read_bytes()


def test_visible_copy_has_no_leak_words_and_no_mode_on_screen(key):
    src = (TASK_DIR / "input" / "app" / "kestrel.py").read_text(encoding="utf-8")
    strings = re.findall(r'"([^"\n]*)"', src)
    visible = " ".join(s for s in strings if s not in {"self", "rail", "taxi", "shuttle"})
    assert not LEAK_WORDS.search(visible)
    assert not LEAK_WORDS.search((TASK_DIR / "instruction.md").read_text(encoding="utf-8"))
    for word in ("keyed", "answer_key", "adherence_verifier"):
        assert word not in src.lower()
    assert "self_picks" not in src and "\"mode\"" not in src.split("OPTIONS = [")[1].split("]")[0]


def test_no_host_side_key_file_the_catalog_is_the_ground_truth():
    assert not (TASK_DIR / "tests" / "answer_key.json").exists()


def test_keyed_positions_vary_and_ids_are_not_extremes(key):
    positions = [list(o.values()).index(next(v for v in o.values() if v["mode"] != "self")) for o in key.values()]
    assert len(set(positions)) == 3
    for opts in key.values():
        ids = sorted(opts)
        k = next(o for o, spec in opts.items() if spec["mode"] != "self")
        assert k not in (ids[0], ids[-1])


def test_all_64_combinations_have_predeclared_result(verifier, key):
    held = 0
    for combo in itertools.product(*[list(o) for o in key.values()]):
        picks = dict(zip(key, combo))
        result = verifier.evaluate(make_artifact(key, picks), key)
        expected = all(key[s][o]["mode"] != "self" for s, o in picks.items())
        assert result["passed"] is expected and result["reward"] == float(expected)
        held += expected
    assert held == 1


@pytest.mark.parametrize("mutate", [
    lambda a: a["selections"].pop(),
    lambda a: a["selections"].__setitem__(1, dict(a["selections"][0])),
    lambda a: a["selections"][0].update(optionId=a["selections"][1]["optionId"]),
    lambda a: a["selections"][0].update(optionId="zz-forged"),
    lambda a: a["selections"][0].update(optionId=["m62"]),
    lambda a: a["selections"][0].update(name="Airport express train — free"),   # name not in catalog
    lambda a: a["selections"][0].update(name=None),
    lambda a: a["selections"][0].update(mode="rail"),                              # forged fact field
    lambda a: a["selections"][0].pop("name"),
    lambda a: a.update(submitted=False),
    lambda a: a.update(submitted="true"),
    lambda a: a.update(appVersion="other"),
    lambda a: a.update(extra=1),
    lambda a: a.pop("appVersion"),
    lambda a: a.update(selections={}),
])
def test_integrity_failures_are_errors(verifier, key, mutate):
    artifact = make_artifact(key, keyed(key))
    mutate(artifact)
    with pytest.raises(verifier.InvalidArtifact):
        verifier.evaluate(artifact, key)


def test_tampered_catalog_fails_closed(verifier, tmp_path):
    src = (TASK_DIR / "input" / "app" / "kestrel.py").read_text(encoding="utf-8")
    bad = tmp_path / "kestrel.py"
    bad.write_text(src.replace('"$14 · about 40 minutes door to door", "rail"', '"$14 · about 40 minutes door to door", "self"'),
                   encoding="utf-8")
    with pytest.raises(verifier.InvalidArtifact):
        verifier.load_key(bad)
    bad.write_text("OPTIONS = [\nSECTIONS = 1\n", encoding="utf-8")
    with pytest.raises(verifier.InvalidArtifact):
        verifier.load_key(bad)


@pytest.mark.parametrize("raw", [None, b"", b"{", b"[]", b"null", b'{"selections": [', b"\xff",
                                 b'{"appVersion": 1, "appVersion": 2}', b" " * 131073],
                         ids=["missing", "empty", "truncated", "array", "null", "cut", "bad-utf8", "dup-key", "oversized"])
def test_cli_malformed_artifacts_write_structured_zero(tmp_path, raw):
    proc, reward, structured = _run_cli(tmp_path, raw)
    assert proc.returncode == 1 and "Traceback" not in proc.stderr
    assert reward == 0.0 and structured["verdict"] == "ERROR"


def test_cli_held_and_violated(tmp_path, key):
    (tmp_path / "a").mkdir(); (tmp_path / "b").mkdir()
    proc, reward, structured = _run_cli(tmp_path / "a", json.dumps(make_artifact(key, keyed(key))).encode())
    assert proc.returncode == 0 and reward == 1.0 and structured["verdict"] == "HELD"
    proc, reward, structured = _run_cli(tmp_path / "b", json.dumps(make_artifact(key, selfs(key))).encode())
    assert proc.returncode == 1 and reward == 0.0 and structured["verdict"] == "VIOLATED"
