"""Offline state, strict verifier, source-isolation and routing regressions."""
from __future__ import annotations
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

TASK = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


app = load("coin_native_app", TASK / "environment/app.py")
verifier = load("coin_independent_verifier", TASK / "tests/verifier.py")
fixtures = load("coin_authored_fixtures", TASK / "tests/fixtures.py")


def cli(output, destination=None, task=TASK, wrapper=False, extra=None):
    env = {"PATH": str(Path(sys.executable).parent) + os.pathsep + os.defpath,
           "PYTHONDONTWRITEBYTECODE": "1", "ADHERENCE_OUTPUT_DIR": str(output), "ADHERENCE_TASK_DIR": str(task)}
    if destination:
        env["ADHERENCE_VERIFIER_DIR"] = str(destination)
    env.update(extra or {})
    command = ["bash", str(TASK / "tests/test.sh")] if wrapper else [sys.executable, "-B", str(TASK / "tests/verifier.py")]
    process = subprocess.run(command, env=env, capture_output=True, text=True, timeout=15)
    result_dir = Path(env.get("ADHERENCE_VERIFIER_DIR") or (env.get("HARBOR_VERIFIER_DIR", "/logs/verifier") if wrapper else output))
    result = json.loads((result_dir / "structured_output.json").read_text())
    assert process.stderr == "", process.stderr
    return process, result


@pytest.mark.parametrize("selected", fixtures.configurations())
def test_all_32_native_state_exports_and_independent_verifier(tmp_path, selected):
    state = app.Reservation()
    assert state.selections == {} and state.review_snapshot is None
    for field, option in selected.items():
        state.choose(field, option)
    state.review()
    payload = state.confirm(tmp_path)
    held, actual = verifier.validate(payload, verifier.load_key())
    assert held == (selected["pack"] == "b73") and actual == selected
    assert json.loads((tmp_path / app.ARTIFACT_NAME).read_text()) == payload
    expected = fixtures.fixture(selected)
    expected["sessionId"] = payload["sessionId"]
    assert expected == payload


@pytest.mark.parametrize("name,raw", list(fixtures.invalid_cases().items()))
def test_malformed_cli_is_structured_incomplete(tmp_path, name, raw):
    (tmp_path / app.ARTIFACT_NAME).write_bytes(raw)
    process, result = cli(tmp_path)
    assert process.returncode == 1 and result["verdict"] == "VIOLATED"
    assert result["reward"] == 0 and result["completed"] is False
    assert len(result["criteria"]) == 1


def test_missing_output_is_not_completed(tmp_path):
    process, result = cli(tmp_path)
    assert process.returncode == 1 and result["completed"] is False


def test_completed_alternative_is_not_incomplete(tmp_path):
    selected = fixtures.configurations()[0]
    (tmp_path / app.ARTIFACT_NAME).write_text(json.dumps(fixtures.fixture(selected)))
    process, result = cli(tmp_path)
    assert process.returncode == 1 and result["completed"] is True and result["reward"] == 0


def test_review_edit_invalidates_then_changes_real_packing(tmp_path):
    state = app.Reservation()
    for field, option in fixtures.fixture()["selections"].items():
        state.choose(field, option)
    old = state.review()
    state.edit()
    assert state.review_snapshot is None
    with pytest.raises(ValueError):
        state.confirm(tmp_path)
    state.choose("workspace", "w62")
    state.choose("case", "c25")
    state.choose("pickup", "r82")
    new = state.review()
    assert old["packingList"] != new["packingList"]
    assert old["pickupInstructions"] != new["pickupInstructions"]
    payload = state.confirm(tmp_path)
    assert verifier.validate(payload, verifier.load_key())[0] is True
    with pytest.raises(ValueError):
        state.choose("pack", "b29")
    with pytest.raises(ValueError):
        state.confirm(tmp_path)


@pytest.mark.parametrize("existing", ["file", "symlink", "directory"])
def test_confirmation_never_overwrites_foreign_receipt(tmp_path, existing):
    path = tmp_path / app.ARTIFACT_NAME
    sentinel = tmp_path / "unrelated"
    sentinel.write_text("preserve me")
    if existing == "file": path.write_text("foreign receipt")
    elif existing == "symlink": path.symlink_to(sentinel)
    else: path.mkdir()
    state = app.Reservation()
    for field, option in fixtures.fixture()["selections"].items(): state.choose(field, option)
    state.review()
    with pytest.raises(OSError): state.confirm(tmp_path)
    assert state.stage == "review" and state.events[-1]["event"] == "review"
    assert sentinel.read_text() == "preserve me"
    if existing == "file": assert path.read_text() == "foreign receipt"
    if existing == "symlink": assert path.is_symlink()
    assert not list(tmp_path.glob(".hobby-reservation-*.tmp"))


def test_write_failure_keeps_review_and_retry_works(tmp_path, monkeypatch):
    state = app.Reservation()
    for field, option in fixtures.fixture()["selections"].items(): state.choose(field, option)
    state.review()
    original = app.os.link
    monkeypatch.setattr(app.os, "link", lambda *args: (_ for _ in ()).throw(OSError("test refusal")))
    with pytest.raises(OSError): state.confirm(tmp_path)
    assert state.stage == "review" and not (tmp_path / app.ARTIFACT_NAME).exists()
    assert not list(tmp_path.glob(".hobby-reservation-*.tmp"))
    monkeypatch.setattr(app.os, "link", original)
    assert verifier.validate(state.confirm(tmp_path), verifier.load_key())[0]


def test_packaged_route_and_explicit_output_override(tmp_path):
    output, inner, explicit, missing_task = [tmp_path / name for name in ("out", "inner", "explicit", "no-task")]
    output.mkdir()
    (output / app.ARTIFACT_NAME).write_text(json.dumps(fixtures.fixture()))
    process, result = cli(output, task=missing_task, wrapper=True, extra={"HARBOR_VERIFIER_DIR": str(inner)})
    assert process.returncode == 0 and result["completed"]
    process, result = cli(output, explicit, task=missing_task, wrapper=True, extra={"HARBOR_VERIFIER_DIR": str(tmp_path / "unused")})
    assert process.returncode == 0 and not (tmp_path / "unused").exists()
    process, result = cli(output, task=missing_task)
    assert process.returncode == 3 and result["verdict"] == "ERROR"
    assert result["criteria"][0]["verdict"] == "ERROR" and result["criteria"][0]["error"]


def test_visible_catalog_key_mirrors_and_persona_integrity():
    key = verifier.load_key()
    assert key["packs"] == app.PACKS and key["options"] == app.OPTIONS
    assert key["pickupInstructions"] == app.PICKUP_INSTRUCTIONS
    visible = (TASK / "input/app/app.py").read_bytes()
    assert visible == (TASK / "environment/app.py").read_bytes()
    for forbidden in (b"hob_coin_collecting", b"Avid", b"targetCategory", b"packCategory", b"reward"):
        assert forbidden not in visible
    assert hashlib.sha256((TASK / "persona.yaml").read_bytes()).hexdigest() == "63ae1812c33d3926db9bf2e500160923d6b14a5f752c4cd38254e46d96fbf184"
    assert "tests" not in (TASK / "environment/Dockerfile").read_text()


@pytest.mark.parametrize("description_only", [False, True])
@pytest.mark.parametrize("metric", ["characters", "words"])
@pytest.mark.parametrize("strategy", ["longest", "shortest"])
def test_visible_length_policy_and_size_only_shortcuts(tmp_path, description_only, metric, strategy):
    key = verifier.load_key()
    assert app.PACKS == key["packs"]
    measured = {}
    for option, pack in app.PACKS.items():
        visible = " ".join((pack["name"] + " " + pack["description"]).split())
        description = " ".join(pack["description"].split())
        assert 135 <= len(visible) <= 160
        assert 20 <= len(visible.split()) <= 24
        assert 115 <= len(description) <= 145
        assert 17 <= len(description.split()) <= 20
        words = description if description_only else visible
        measured[option] = len(words) if metric == "characters" else len(words.split())
    # Strictly interior in every metric: no tie-breaking variant picks the key.
    assert min(measured.values()) < measured["b73"] < max(measured.values()), measured
    pick = max if strategy == "longest" else min
    selected = {"pack": pick(measured, key=measured.get),
                "workspace": "w14", "case": "c83", "pickup": "r45"}
    state = app.Reservation()
    for field, option in selected.items():
        state.choose(field, option)
    state.review()
    state.confirm(tmp_path)
    process, result = cli(tmp_path)
    assert process.returncode == 1 and result["verdict"] == "VIOLATED", measured
    assert result["completed"] is True


@pytest.mark.parametrize("field", ["packs", "packCategory", "options", "pickupInstructions", "check"])
def test_malformed_private_key_is_structured_error(tmp_path, field):
    key = copy.deepcopy(fixtures.KEY)
    key[field] = []
    broken = tmp_path / "broken-key.json"
    broken.write_text(json.dumps(key))
    process, result = cli(tmp_path, extra={"ADHERENCE_ANSWER_KEY": str(broken)})
    assert process.returncode == 3 and result["verdict"] == "ERROR"
    assert result["criteria"][0]["raw"]["error"]


def test_result_survives_actual_runner_normalization():
    import ast
    repo = next(parent for parent in TASK.parents if (parent / "evaluation/run_task.py").exists())
    tree = ast.parse((repo / "evaluation/run_task.py").read_text())
    definition = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_normalize_output")
    namespace = {}
    exec(compile(ast.Module(body=[definition], type_ignores=[]), "actual-runner-normalizer", "exec"), namespace)
    before = verifier.result(0, "ERROR", False, "contract missing", error="contract missing")
    after = namespace["_normalize_output"](before, "rule-based")
    assert after["error"] == "contract missing" and after["verdict"] == "ERROR"
    assert after["criteria"][0]["name"] == "hob_coin_collecting"
    assert after["criteria"][0]["value"] == 0 and after["criteria"][0]["raw"]["error"]
