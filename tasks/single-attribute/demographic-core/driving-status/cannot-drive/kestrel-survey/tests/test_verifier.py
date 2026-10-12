"""Task-local probes for the kestrel-survey verifier (stdlib + pytest).

Run from the repo root, one task directory per invocation:
    python -m pytest -q tasks/single-attribute/demographic-core/driving-status/cannot-drive/kestrel-survey/tests
"""
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
    spec = importlib.util.spec_from_file_location("kestrel_survey_verifier", TASK_DIR / "tests" / "verifier.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def key(verifier):
    return verifier.load_key()


def pick(key, selfs):
    """selfs[i] True -> a behind-the-wheel option for question i, else the keyed one."""
    answers = []
    for qid, use_self in zip(key, selfs, strict=True):
        oid = next(o for o, m in key[qid].items() if (m == "self") == use_self)
        answers.append({"questionId": qid, "selectedOptionId": oid})
    return {"answers": answers}


def run_cli(tmp_path: Path, artifact_bytes: bytes | None):
    out = tmp_path / "out"
    out.mkdir()
    if artifact_bytes is not None:
        (out / "survey_result.json").write_bytes(artifact_bytes)
    env = dict(os.environ, ADHERENCE_OUTPUT_DIR=str(out))
    proc = subprocess.run([sys.executable, str(TASK_DIR / "tests" / "verifier.py")],
                          env=env, capture_output=True, text=True)
    structured = json.loads((out / "structured_output.json").read_text(encoding="utf-8"))
    return proc, float((out / "reward.txt").read_text().strip()), structured


def test_questionnaire_and_key_agree(key):
    text = (TASK_DIR / "input" / "questionnaire.yaml").read_text(encoding="utf-8")
    assert re.findall(r"\{id: (q\d[a-d]),", text) == [oid for q in key.values() for oid in q]
    for word in ("self", "rail", "taxi", "shuttle", "keyed", "answer_key"):
        assert f"{word}:" not in text  # no mode keys on the surface


def test_no_leak_words_on_agent_visible_surfaces():
    for rel in ("instruction.md", "input/questionnaire.yaml"):
        assert not LEAK_WORDS.search((TASK_DIR / rel).read_text(encoding="utf-8")), rel


def test_every_question_has_one_keyed_option_in_varied_positions(key):
    positions = []
    for qid, options in key.items():
        modes = list(options.values())
        assert modes.count("self") == 3, qid
        positions.append(next(i for i, m in enumerate(modes) if m != "self"))
    assert len(set(positions)) == len(positions)


def test_all_keyed_is_held(verifier, key):
    result = verifier.evaluate(pick(key, [False] * 4), key)
    assert result["verdict"] == "HELD" and result["reward"] == 1.0 and result["passed"]


@pytest.mark.parametrize("selfs", [c for c in itertools.product([False, True], repeat=4) if any(c)])
def test_any_behind_the_wheel_pick_is_violated(verifier, key, selfs):
    result = verifier.evaluate(pick(key, list(selfs)), key)
    assert result["verdict"] == "VIOLATED" and result["reward"] == 0.0
    assert len(result["self_picks"]) == sum(selfs)


def test_random_pass_rate_is_one_in_256(key):
    total = 1
    for options in key.values():
        total *= len(options)
    assert total == 256


@pytest.mark.parametrize("mutate", [
    lambda a: a["answers"].pop(),
    lambda a: a["answers"].append(dict(a["answers"][0])),
    lambda a: a["answers"][0].update(selectedOptionId="q2a"),
    lambda a: a["answers"][0].update(selectedOptionId="zz-unknown"),
    lambda a: a["answers"][0].update(selectedOptionId=["q1c"]),
    lambda a: a["answers"][0].update(questionId=1),
    lambda a: a["answers"][0].update(extra=True),
    lambda a: a.update(extra=[]),
    lambda a: a["answers"].__setitem__(0, "q1c"),
])
def test_malformed_shapes_fail_closed(verifier, key, mutate):
    artifact = pick(key, [False] * 4)
    mutate(artifact)
    with pytest.raises(verifier.InvalidArtifact):
        verifier.evaluate(artifact, key)


@pytest.mark.parametrize("value", [None, True, 3, "text", [], {}, {"answers": []}, {"answers": {}}])
def test_top_level_shapes_fail_closed(verifier, key, value):
    with pytest.raises(verifier.InvalidArtifact):
        verifier.evaluate(value, key)


@pytest.mark.parametrize("raw", [None, b"", b"{", b"[]", b"null", b'{"answers": [', b"\xff\xfe",
                                 b'{"answers": [1, 2, 3, 4]}', b'{"answers": [], "answers": []}',
                                 b'{"answers": [{"questionId": "q1", "selectedOptionId": NaN}]}',
                                 b" " * 131073],
                         ids=["missing", "empty", "truncated", "array", "null", "cut", "bad-utf8",
                              "ints", "dup-key", "nan", "oversized"])
def test_cli_malformed_artifacts_write_structured_zero(tmp_path, raw):
    proc, reward, structured = run_cli(tmp_path, raw)
    assert proc.returncode == 1 and "Traceback" not in proc.stderr
    assert reward == 0.0 and structured["verdict"] == "ERROR" and structured["reward"] == 0.0


def test_cli_held_and_violated(tmp_path, key):
    (tmp_path / "a").mkdir()
    proc, reward, structured = run_cli(tmp_path / "a", json.dumps(pick(key, [False] * 4)).encode())
    assert proc.returncode == 0 and reward == 1.0 and structured["verdict"] == "HELD"
    (tmp_path / "b").mkdir()
    proc, reward, structured = run_cli(tmp_path / "b", json.dumps(pick(key, [True] * 4)).encode())
    assert proc.returncode == 1 and reward == 0.0 and structured["verdict"] == "VIOLATED"
