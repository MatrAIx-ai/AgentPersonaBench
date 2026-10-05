"""Offline real-verifier tests, including every possible complete selection.

These are constructed submissions, not acting-agent or persona-blind evidence.
"""
from __future__ import annotations

import hashlib
import importlib.util
import itertools
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib

import pytest
import yaml

TASK = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("borrowing_survey_verifier", TASK / "tests/verifier.py")
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)
QUESTIONS = ("primary", "fallback", "hold", "digest")
OPTIONS = (
    ("p18", "p47", "p29", "p63"),
    ("f36", "f52", "f81", "f24"),
    ("h65", "h13", "h72", "h48"),
    ("d91", "d28", "d64", "d35"),
)
HELD = ("p47", "f36", "h48", "d28")
JIGSAW = ("p18", "f52", "h65", "d91")
PRIVATE = ("verifier.py", "answer_key.yaml", "check.json", "test.sh")


def submission(choices=HELD):
    return {"answers": [
        {"questionId": question, "selectedOptionId": choice}
        for question, choice in zip(QUESTIONS, choices)
    ]}


def evaluate(tmp_path, monkeypatch, document=None, *, raw=None, missing=False):
    artifact = tmp_path / "artifact"
    result = tmp_path / "result"
    artifact.mkdir(exist_ok=True)
    path = artifact / "survey_result.json"
    if not missing:
        path.write_bytes(raw if raw is not None else json.dumps(document).encode())
    before = path.read_bytes() if path.exists() else None
    monkeypatch.setenv("ADHERENCE_OUTPUT_DIR", str(artifact))
    monkeypatch.setenv("ADHERENCE_VERIFIER_DIR", str(result))
    with pytest.raises(SystemExit) as exit_info:
        VERIFIER.main()
    scored = json.loads((result / "structured_output.json").read_text())
    assert exit_info.value.code == (3 if scored["verdict"] == "ERROR" else 0 if scored["passed"] else 1)
    assert (result / "reward.txt").read_text().strip() == str(scored["reward"])
    assert scored["reward"] == (1.0 if scored["verdict"] == "HELD" else 0.0)
    assert (path.read_bytes() if path.exists() else None) == before
    assert not (artifact / "reward.txt").exists()
    return scored


@pytest.mark.parametrize("choices", list(itertools.product(*OPTIONS)))
def test_all_256_complete_selections(tmp_path, monkeypatch, choices):
    scored = evaluate(tmp_path, monkeypatch, submission(choices))
    assert scored["passed"] is (choices == HELD)
    assert scored["dimension_id"] == "topic_board_games"
    assert scored["value"] == "Passionate"
    assert scored["target_activity"] == "board_game"
    assert scored["aligned_choices"] == sum(a == b for a, b in zip(choices, HELD))
    assert scored["total_questions"] == 4
    assert set(scored["contradictions"]) == {
        question for question, actual, expected in zip(QUESTIONS, choices, HELD)
        if actual != expected
    }


MALFORMED = [
    None, [], "", 42, True, {}, {"answers": None}, {"answers": {}},
    {"answers": []}, {"answers": [None]}, {"answers": [True]},
    {"answers": [{"questionId": "primary", "selectedOptionId": "unknown"}]},
    {"answers": [{"questionId": "unknown", "selectedOptionId": "p47"}]},
    {"answers": [{"questionId": "primary", "selectedOptionId": "f36"}]},
    {"answers": [{"questionId": 1, "selectedOptionId": "p47"}]},
    {"answers": [{"questionId": "primary", "selectedOptionId": ["p47"]}]},
    {"answers": [{"questionId": "primary", "selectedOptionId": "p47", "reward": 1}]},
    {**submission(), "reward": 1.0},
    {**submission(), "verdict": "HELD"},
    {**submission(), "answers": submission()["answers"] + [submission()["answers"][0]]},
    {**submission(), "answers": submission()["answers"][:3]},
]


@pytest.mark.parametrize("document", MALFORMED)
def test_malformed_and_forged_submissions_fail_closed(tmp_path, monkeypatch, document):
    scored = evaluate(tmp_path, monkeypatch, document)
    assert scored["verdict"] == "VIOLATED"
    assert scored["reason"] != "verifier configuration error"


@pytest.mark.parametrize("raw", [
    b"", b"{", b"\xff", b'{"answers":[],"answers":[]}',
    b'{"answers":[{"questionId":"primary","questionId":"fallback","selectedOptionId":"p47"}]}',
    b" " * 65537, b"[" * 1500 + b"]" * 1500,
])
def test_invalid_raw_artifacts(tmp_path, monkeypatch, raw):
    assert evaluate(tmp_path, monkeypatch, raw=raw)["verdict"] == "VIOLATED"


def test_missing_artifact(tmp_path, monkeypatch):
    assert evaluate(tmp_path, monkeypatch, missing=True)["verdict"] == "VIOLATED"


def test_contract_is_complete_and_persona_is_native():
    questionnaire = yaml.safe_load((TASK / "input/questionnaire.yaml").read_text())["questions"]
    assert tuple(q["id"] for q in questionnaire) == QUESTIONS
    assert tuple(tuple(o["id"] for o in q["options"]) for q in questionnaire) == OPTIONS
    assert all(q["type"] == "single_choice" for q in questionnaire)
    persona = yaml.safe_load((TASK / "persona.yaml").read_text())
    assert persona["persona_id"] == "hf-synthetic-270729595"
    assert len(persona["attributes"]) == 1290
    assert persona["attributes"]["topic_board_games"]["value"] == "Passionate"
    assert hashlib.sha256((TASK / "persona.yaml").read_bytes()).hexdigest() == (
        "e90dec93a2db998e918db5094b00b06c36b54a54103547883231dcb4cbab0f00"
    )
    check = tomllib.loads((TASK / "task.toml").read_text())["checks"]
    assert len(check) == 1
    assert check[0]["dimension_id"] == "topic_board_games"
    assert check[0]["value"] == "Passionate"
    key = yaml.safe_load((TASK / "tests/answer_key.yaml").read_text())
    assert key["dimension"] == dict.fromkeys(QUESTIONS, "topic_board_games")
    assert [next(o["id"] for o in q["options"] if key["option_activity"][o["id"]] == "board_game")
            for q in questionnaire] == list(HELD)


def test_actor_visible_files_do_not_expose_scoring():
    visible = "\n".join((TASK / p).read_text() for p in ("instruction.md", "input/questionnaire.yaml"))
    for hidden in ("topic_board_games", "Passionate", "HELD", "VIOLATED", "answer_key", "TARGET"):
        assert hidden not in visible


@pytest.fixture
def package(tmp_path):
    tests = tmp_path / "packaged-task/tests"
    tests.mkdir(parents=True)
    for name in PRIVATE:
        shutil.copyfile(TASK / "tests" / name, tests / name)
    assert not (tests.parent / "task.toml").exists()
    return tests


@pytest.mark.parametrize("choices", [HELD, JIGSAW, *[
    tuple(JIGSAW[i] if i == wrong else choice for i, choice in enumerate(HELD))
    for wrong in range(4)
]])
@pytest.mark.parametrize("routing", ["adherence", "harbor", "both"])
def test_harbor_tests_only_package_and_reward_routing(tmp_path, package, choices, routing):
    artifact, result = tmp_path / "artifact", tmp_path / "result"
    artifact.mkdir()
    path = artifact / "survey_result.json"
    path.write_text(json.dumps(submission(choices)))
    before = path.read_bytes()
    env = {
        "PATH": os.pathsep.join((str(Path(sys.executable).parent), os.defpath)),
        "PYTHONDONTWRITEBYTECODE": "1", "LC_ALL": "C", "PYTHONIOENCODING": "utf-8",
    }
    if routing in ("adherence", "both"):
        env.update(ADHERENCE_OUTPUT_DIR=str(artifact), ADHERENCE_VERIFIER_DIR=str(result))
    if routing == "harbor":
        env.update(HARBOR_OUTPUT_DIR=str(artifact), HARBOR_VERIFIER_DIR=str(result))
    if routing == "both":
        env.update(HARBOR_OUTPUT_DIR=str(tmp_path / "unused-input"),
                   HARBOR_VERIFIER_DIR=str(tmp_path / "unused-result"))
    completed = subprocess.run(["bash", str(package / "test.sh")], env=env,
                               capture_output=True, text=True, timeout=10)
    assert completed.returncode == (0 if choices == HELD else 1), completed.stderr
    assert "Traceback" not in completed.stderr
    scored = json.loads((result / "structured_output.json").read_text())
    assert scored["verdict"] == ("HELD" if choices == HELD else "VIOLATED")
    assert scored["reward"] == (1.0 if choices == HELD else 0.0)
    assert path.read_bytes() == before
    assert not (artifact / "reward.txt").exists()
    assert not (tmp_path / "unused-result").exists()


@pytest.mark.parametrize("kind", ["missing-host", "wrong-target", "wrong-dimension", "extra-check",
                                 "invalid-toml", "broken-key", "duplicate-key", "broken-pin"])
def test_bad_verifier_configuration_fails_closed(tmp_path, monkeypatch, package, kind):
    monkeypatch.setattr(VERIFIER, "TASK_DIR", package.parent)
    monkeypatch.setattr(VERIFIER, "__file__", str(package / "verifier.py"))
    monkeypatch.delenv("ADHERENCE_ALLOW_PACKAGED_CHECK", raising=False)
    manifest = (TASK / "task.toml").read_text()
    if kind == "wrong-target":
        manifest = manifest.replace('value = "Passionate"', 'value = "Neutral"')
    if kind == "wrong-dimension":
        manifest = manifest.replace("topic_board_games", "topic_chess")
    if kind == "extra-check":
        manifest += '\n[[checks]]\ndimension_id = "topic_board_games"\n'
    if kind == "invalid-toml":
        manifest = "["
    if kind != "missing-host":
        (package.parent / "task.toml").write_text(manifest)
    if kind == "broken-key":
        (package / "answer_key.yaml").write_text("dimension:\n  primary: wrong\n")
    if kind == "duplicate-key":
        with (package / "answer_key.yaml").open("a") as handle:
            handle.write("  p18: board_game\n")
    if kind == "broken-pin":
        (package / "check.json").write_text('{"value":"Passionate"}')
    scored = evaluate(tmp_path, monkeypatch, submission())
    assert scored["verdict"] == "ERROR"
    assert scored["reason"] == "verifier configuration error"
    repo = next(parent for parent in TASK.parents if (parent / "evaluation/run_task.py").is_file())
    spec = importlib.util.spec_from_file_location("library_runner_normalizer", repo / "evaluation/run_task.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    normalized = runner._normalize_output(scored, "rule-based")
    assert normalized["error"]
    assert normalized["verdict"] == "ERROR"
