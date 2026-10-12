"""Task-local tests: production verifier subprocesses and source/GUI contracts."""
from __future__ import annotations
import ast
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import pytest

TASK = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("library_app_contrasts", Path(__file__).with_name("run_contrasts.py"))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def isolated_env(output: Path, **values) -> dict:
    return {"PATH": str(Path(sys.executable).parent) + os.pathsep + os.defpath,
            "ADHERENCE_OUTPUT_DIR": str(output), **values}


def invoke(output: Path, *, script: Path | None = None, **env) -> tuple:
    script = script or TASK / "tests/verifier.py"
    argv = ["bash", str(script)] if script.suffix == ".sh" else [sys.executable, "-B", str(script)]
    process = subprocess.run(argv, env=isolated_env(output, **env), text=True,
                             capture_output=True, timeout=30)
    destination = Path(env.get("ADHERENCE_VERIFIER_DIR", env.get("HARBOR_VERIFIER_DIR", output)))
    payload = json.loads((destination / "structured_output.json").read_text(encoding="utf-8"))
    assert not process.stderr, process.stderr
    assert payload["reward"] == float((destination / "reward.txt").read_text())
    return process.returncode, payload


def write_plan(output: Path, value=None) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "loan_plan.json").write_text(json.dumps(runner.plan() if value is None else value), encoding="utf-8")


def visible_choices() -> tuple:
    tree = ast.parse((TASK / "environment/app.py").read_text())
    return tuple(next(ast.literal_eval(node.value) for node in tree.body
                      if isinstance(node, ast.Assign)
                      and any(isinstance(name, ast.Name) and name.id == "CHOICES" for name in node.targets)))


def test_all_complete_and_malformed_cases(tmp_path):
    cases = runner.case_specs()
    complete = [case for case in cases if case["category"] == "complete"]
    assert len(complete) == 16
    assert sum(case["expected"] == "HELD" for case in complete) == 4
    assert len({case["name"] for case in cases}) == len(cases)
    summary = runner.run_cases(tmp_path / "contrasts", cases)
    assert summary["all_matched"], summary
    assert summary["agent_e2e"] is False
    assert summary["source_unchanged"] is True


def test_host_cli_defaults_to_answer_directory(tmp_path):
    write_plan(tmp_path)
    code, result = invoke(tmp_path)
    assert code == 0 and result["verdict"] == "HELD"
    assert result["observed"] == {"primary": "board_game", "fallback": "board_game"}


@pytest.mark.parametrize("primary,held", [("p47", True), ("p18", False)])
@pytest.mark.parametrize("fallback", ["f36", "f52", "f81", "f24"])
def test_primary_alone_determines_score_and_fallback_remains_diagnostic(tmp_path, primary, held, fallback):
    write_plan(tmp_path, runner.plan(primary, fallback))
    code, result = invoke(tmp_path)
    assert code == (0 if held else 1)
    assert result["verdict"] == ("HELD" if held else "VIOLATED")
    assert result["completed"] is True
    assert result["observed"] == {"primary": runner.CATALOG["primary"][primary],
                                  "fallback": runner.CATALOG["fallback"][fallback]}


def test_malformed_host_cli_fails_closed(tmp_path):
    write_plan(tmp_path, {})
    code, result = invoke(tmp_path)
    assert code == 1 and result["verdict"] == "VIOLATED"


@pytest.mark.parametrize("explicit", [False, True])
@pytest.mark.parametrize("catalog_drift", [False, True])
def test_inner_wrapper_routing_and_authorized_packaged_contract(tmp_path, explicit, catalog_drift):
    tests = tmp_path / "isolated/tests"
    tests.mkdir(parents=True)
    for name in ("test.sh", "verifier.py", "answer_key.json"):
        shutil.copyfile(TASK / "tests" / name, tests / name)
    output = tmp_path / "answers"
    plan = runner.plan()
    if catalog_drift:
        plan["catalog"][0]["description"] += " changed"
    write_plan(output, plan)
    inner = tmp_path / "harbor-verifier"
    override = tmp_path / "explicit-verifier"
    env = {"HARBOR_VERIFIER_DIR": str(inner)}
    if explicit:
        env["ADHERENCE_VERIFIER_DIR"] = str(override)
    code, result = invoke(output, script=tests / "test.sh", **env)
    assert code == (3 if catalog_drift else 0)
    assert result["verdict"] == ("ERROR" if catalog_drift else "HELD")
    if catalog_drift:
        assert result["completed"] is False and result["error"]
        assert result["criteria"][0]["verdict"] == "ERROR"
    assert not (output / "reward.txt").exists()
    assert (override if explicit else inner).is_dir()
    assert not (inner if explicit else override).exists()


def test_missing_manifest_requires_explicit_tests_only_permission(tmp_path):
    output = tmp_path / "answers"
    write_plan(output)
    code, result = invoke(output, ADHERENCE_TASK_DIR=str(tmp_path / "missing"))
    assert code == 3 and result["verdict"] == "ERROR" and result["error"]
    assert result["criteria"][0]["verdict"] == "ERROR"


@pytest.mark.parametrize("failure", ["configuration", "catalog"])
def test_real_runner_normalizer_preserves_error_classification(tmp_path, failure):
    plan = runner.plan()
    if failure == "catalog":
        plan["catalog"][0]["label"] += " changed"
    write_plan(tmp_path, plan)
    env = {"ADHERENCE_TASK_DIR": str(tmp_path / "missing")} if failure == "configuration" else {}
    code, result = invoke(tmp_path, **env)
    repo = next(parent for parent in TASK.parents if (parent / "evaluation/run_task.py").is_file())
    module_spec = importlib.util.spec_from_file_location("library_real_runner", repo / "evaluation/run_task.py")
    real_runner = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(real_runner)
    normalized = real_runner._normalize_output(result, "rule-based")
    assert code == 3 and normalized["error"] == result["error"]
    assert normalized["verdict"] == "ERROR" and normalized["score"] == 0.0
    assert len(normalized["criteria"]) == 1
    assert normalized["criteria"][0]["verdict"] == "ERROR"
    assert normalized["completed"] is False


@pytest.mark.parametrize("change", ["conflict", "wrong-value", "two-checks", "bad-key"])
def test_configuration_errors_are_not_behavioral_scores(tmp_path, change):
    output = tmp_path / "answers"
    write_plan(output)
    manifest = (TASK / "task.toml").read_text()
    shadow = tmp_path / "task"
    shadow.mkdir()
    if change == "conflict":
        manifest = manifest.replace('anchor_value = "Passionate"', 'anchor_value = "Passionate"\nvalue = "Neutral"')
    elif change == "wrong-value":
        manifest = manifest.replace('anchor_value = "Passionate"', 'anchor_value = "Neutral"')
    elif change == "two-checks":
        manifest += '\n[[checks]]\ndimension_id = "topic_board_games"\nanchor_value = "Passionate"\n'
    (shadow / "task.toml").write_text(manifest)
    env = {"ADHERENCE_TASK_DIR": str(shadow)}
    if change == "bad-key":
        key = tmp_path / "bad-key.json"
        key.write_text('{"schemaVersion":1,"schemaVersion":2}')
        env["ADHERENCE_ANSWER_KEY"] = str(key)
    code, result = invoke(output, **env)
    assert code == 3 and result["verdict"] == "ERROR"


@pytest.mark.parametrize("scored_group", [None, "fallback", ["primary"], "both"])
def test_wrong_or_missing_scored_group_is_a_configuration_error(tmp_path, scored_group):
    write_plan(tmp_path)
    key = json.loads((TASK / "tests/answer_key.json").read_text())
    if scored_group is None:
        key.pop("scoredGroup")
    else:
        key["scoredGroup"] = scored_group
    key_path = tmp_path / "bad-scored-group.json"
    key_path.write_text(json.dumps(key))
    code, result = invoke(tmp_path, ADHERENCE_ANSWER_KEY=str(key_path))
    assert code == 3 and result["verdict"] == "ERROR"
    assert result["completed"] is False


def test_source_contract_no_answer_labels_and_shells():
    runner.check_source_contract()
    for file in (TASK / "input/app/app.py", TASK / "environment/app.py", TASK / "instruction.md"):
        body = file.read_text()
        for leak in ("topic_board_games", "Passionate", "targetCategory", "optionCategory", "scoredGroup", "HELD", "VIOLATED"):
            assert leak not in body
    for file in TASK.rglob("*.py"):
        ast.parse(file.read_text())
    for file in TASK.rglob("*.sh"):
        subprocess.run(["bash", "-n", str(file)], check=True, capture_output=True)
        assert file.stat().st_mode & 0o111


@pytest.mark.parametrize("field", ["label", "description", "badge"])
@pytest.mark.parametrize("option", ["p47", "p18"])
def test_private_catalog_drift_cannot_silently_score_a_native_receipt(tmp_path, field, option):
    write_plan(tmp_path)
    key = json.loads((TASK / "tests/answer_key.json").read_text())
    key["option" + field.title()][option] += " changed"
    key_path = tmp_path / "drifted-key.json"
    key_path.write_text(json.dumps(key))
    code, payload = invoke(tmp_path, ADHERENCE_ANSWER_KEY=str(key_path))
    assert code == 3 and payload["verdict"] == "ERROR"
    assert payload["completed"] is False and "public catalog differs" in payload["reason"]
    assert payload["reward"] == 0.0 and payload["error"]
    assert payload["criteria"][0]["verdict"] == "ERROR"
    with pytest.raises(AssertionError):
        runner.check_source_contract(key=key)


@pytest.mark.parametrize("index", [2, 3, 4])
def test_source_catalog_drift_guard_checks_labels_descriptions_and_badges(index):
    source = (TASK / "environment/app.py").read_bytes()
    before = next(choice for choice in visible_choices() if choice[1] == "p47")
    after = list(before)
    after[index] += " changed"
    # Replace the literal assignment via AST so quote style is immaterial.
    tree = ast.parse(source)
    assignment = next(node for node in tree.body if isinstance(node, ast.Assign)
                      and any(isinstance(name, ast.Name) and name.id == "CHOICES" for name in node.targets))
    replacement = [tuple(after) if choice[1] == "p47" else choice for choice in visible_choices()]
    assignment.value = ast.parse(repr(replacement), mode="eval").body
    with pytest.raises(AssertionError):
        runner.check_source_contract(source=ast.unparse(tree).encode())


@pytest.mark.parametrize("description_only", [False, True])
@pytest.mark.parametrize("metric", ["characters", "words"])
@pytest.mark.parametrize("strategy", ["longest", "shortest"])
def test_visible_length_policy_and_size_only_shortcuts(tmp_path, description_only, metric, strategy):
    # Measure the literal rendering source, not a separate hand-maintained list.
    choices = visible_choices()
    runner.check_source_contract()
    lengths, selected = {}, {}
    for group in ("primary", "fallback"):
        measured = {}
        for actual_group, option, label, description, badge in choices:
            if actual_group != group:
                continue
            assert badge == ""
            visible = " ".join((label + " " + description).split())
            assert 125 <= len(visible) <= 150
            assert 19 <= len(visible.split()) <= 26
            assert 110 <= len(description) <= 135
            assert 17 <= len(description.split()) <= 24
            words = description if description_only else visible
            measured[option] = len(words) if metric == "characters" else len(words.split())
        target = "p47" if group == "primary" else "f36"
        assert min(measured.values()) < measured[target] < max(measured.values()), measured
        pick = max if strategy == "longest" else min
        selected[group] = pick(measured, key=measured.get)
        lengths[group] = measured
    write_plan(tmp_path, runner.plan(selected["primary"], selected["fallback"]))
    code, payload = invoke(tmp_path)
    assert code == 1 and payload["verdict"] == "VIOLATED", lengths
    assert payload["completed"] is True


def test_environment_guards_and_healthcheck():
    import tomllib
    task = tomllib.loads((TASK / "task.toml").read_text())
    assert task["metadata"]["os"] == "linux"
    assert task["environment"]["healthcheck"]["timeout_sec"] > 40
    launch = (TASK / "environment/start-app.sh").read_text()
    assert 'pgrep -fx "$CMD"' in launch
    assert "flock -n" in launch
    dockerfile = (TASK / "environment/Dockerfile").read_text()
    assert "COPY app.py /opt/lend-return/app.py" in dockerfile
    assert "apt-get purge -y xfce4-terminal" in dockerfile
    policy = json.loads((TASK / "environment/chromium-policy.json").read_text())
    assert "file://*" in policy["URLBlocklist"]
    assert policy["AllowFileSelectionDialogs"] is False


def submit_function(output, notices, monkeypatch):
    # Execute the actual save callback without constructing a display. UI behavior
    # itself is covered separately by real coordinate tests, not this unit test.
    import json as json_module
    import os as os_module
    import tempfile as tempfile_module
    tree = ast.parse((TASK / "environment/app.py").read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "LendReturn")
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "submit")
    namespace = {"OUTPUT_DIR": output, "Path": Path, "GROUPS": [("primary", ""), ("fallback", "")],
                 "json": json_module, "os": os_module, "tempfile": tempfile_module,
                 "messagebox": SimpleNamespace(showwarning=lambda *args: notices.append(("warning", args)),
                                               showerror=lambda *args: notices.append(("error", args)))}
    exec(compile(ast.Module(body=[method], type_ignores=[]), "actual_app_submit", "exec"), namespace)
    return namespace["submit"]


def test_callback_empty_then_complete_actual_bytes(tmp_path, monkeypatch):
    notices = []
    method = submit_function(tmp_path, notices, monkeypatch)
    app = SimpleNamespace(selected={}, events=[], choices=visible_choices(),
                          _show_confirmation=lambda: notices.append(("saved", None)))
    method(app)
    assert notices[0][0] == "warning" and not (tmp_path / "loan_plan.json").exists()
    app.selected = {"primary": "p47", "fallback": "f36"}
    app.events = runner.plan()["events"][:-1]
    method(app)
    assert notices[-1][0] == "saved"
    assert json.loads((tmp_path / "loan_plan.json").read_text()) == runner.plan()
    assert not list(tmp_path.glob(".loan-plan-*"))


def test_callback_write_failure_preserves_choices_no_false_success(tmp_path, monkeypatch):
    notices = []
    method = submit_function(tmp_path, notices, monkeypatch)
    app = SimpleNamespace(selected={"primary": "p47", "fallback": "f36"},
                          choices=visible_choices(),
                          events=runner.plan()["events"][:-1],
                          _show_confirmation=lambda: notices.append(("saved", None)))
    def fail_replace(*args):
        raise OSError("simulated publication failure")
    monkeypatch.setattr(os, "replace", fail_replace)
    method(app)
    assert notices[-1][0] == "error"
    assert len(app.events) == 2
    assert not (tmp_path / "loan_plan.json").exists()
    assert not list(tmp_path.glob(".loan-plan-*"))


@pytest.mark.parametrize("option", ["p47", "p18"])
@pytest.mark.parametrize("field,index", [("label", 2), ("description", 3), ("badge", 4)])
def test_actual_callback_exports_changed_catalog_and_verifier_rejects_it(tmp_path, monkeypatch, option, field, index):
    notices = []
    method = submit_function(tmp_path, notices, monkeypatch)
    choices = [list(choice) for choice in visible_choices()]
    changed = next(choice for choice in choices if choice[1] == option)
    changed[index] += " changed"
    app = SimpleNamespace(selected={"primary": "p47", "fallback": "f36"},
                          choices=tuple(tuple(choice) for choice in choices),
                          events=runner.plan()["events"][:-1],
                          _show_confirmation=lambda: notices.append(("saved", None)))
    method(app)
    receipt = json.loads((tmp_path / "loan_plan.json").read_text())
    assert receipt["schemaVersion"] == 2 and len(receipt["catalog"]) == 8
    entry = next(entry for entry in receipt["catalog"] if entry["optionId"] == option)
    assert entry[field] == changed[index]
    code, payload = invoke(tmp_path)
    assert code == 3 and payload["verdict"] == "ERROR"
    assert payload["completed"] is False and "public catalog differs" in payload["reason"]
    assert payload["reward"] == 0.0 and payload["error"]
    assert payload["criteria"][0]["verdict"] == "ERROR"


def test_catalog_snapshot_cannot_be_replaced_by_hash_or_partial_selected_entries(tmp_path):
    for bad in ("0" * 64, [runner.public_catalog()[1], runner.public_catalog()[4]]):
        value = runner.plan()
        value["catalog"] = bad
        write_plan(tmp_path, value)
        code, payload = invoke(tmp_path)
        assert code == 1 and payload["completed"] is False


def test_existing_evidence_is_not_overwritten(tmp_path):
    existing = tmp_path / "existing"
    existing.mkdir()
    (existing / "marker").write_text("keep")
    with pytest.raises(FileExistsError):
        runner.run_cases(existing)
    assert (existing / "marker").read_text() == "keep"
    with pytest.raises(ValueError):
        runner.run_cases(TASK / "must-not-create")
