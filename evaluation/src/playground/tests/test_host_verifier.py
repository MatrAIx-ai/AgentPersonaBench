from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from playground.host_verifier import maybe_run_host_verifier, source_relative_path


def _artifact_source(tmp_root: Path) -> str:
    return str(tmp_root / "submission")


def _test_sh(artifact_source: str) -> str:
    return f"""\
#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PY'
import json
import os
from pathlib import Path

OUTPUT_DIR = Path(
    os.environ.get("PLAYGROUND_OUTPUT_DIR")
    or os.environ.get("MATRIX_OUTPUT_DIR")
    or os.environ.get("HARBOR_OUTPUT_DIR")
    or {artifact_source!r}
)
decision_path = OUTPUT_DIR / "decision.json"
if not decision_path.is_file():
    raise SystemExit("missing decision.json")

verifier_dir = Path(os.environ.get("HARBOR_VERIFIER_DIR") or "/logs/verifier")
verifier_dir.mkdir(parents=True, exist_ok=True)
(verifier_dir / "reward.txt").write_text("1")
(verifier_dir / "structured_output.json").write_text(json.dumps({{"ok": True}}))
PY
"""


def _write_fake_task(
    repo_root: Path, task_rel: str, *, artifact_source: str, timeout_sec: float = 30.0
) -> None:
    task_dir = repo_root / task_rel
    (task_dir / "tests").mkdir(parents=True, exist_ok=True)
    (task_dir / "task.toml").write_text(
        (
            f'artifacts = ["{artifact_source}"]\n'
            f"[verifier]\ntimeout_sec = {timeout_sec}\n"
        ),
        encoding="utf-8",
    )
    (task_dir / "tests" / "test.sh").write_text(
        _test_sh(artifact_source), encoding="utf-8"
    )


def _write_trial(
    trial_dir: Path,
    task_rel: str,
    *,
    artifact_source: str,
    with_decision: bool,
    with_exception: bool,
) -> None:
    trial_dir.mkdir(parents=True, exist_ok=True)
    (trial_dir / "config.json").write_text(
        json.dumps({"task": {"path": task_rel}}), encoding="utf-8"
    )
    downloaded_dir = trial_dir / "artifacts" / Path(source_relative_path(artifact_source))
    downloaded_dir.mkdir(parents=True, exist_ok=True)
    if with_decision:
        (downloaded_dir / "decision.json").write_text("{}", encoding="utf-8")

    result_payload: dict = {}
    if with_exception:
        result_payload["exception_info"] = {
            "exception_type": "RewardFileNotFoundError",
            "exception_message": "No reward file found",
        }
    (trial_dir / "result.json").write_text(json.dumps(result_payload), encoding="utf-8")


def test_source_relative_path_matches_harbor_mapping():
    assert str(source_relative_path("/app/output")) == "app/output"


def test_host_verifier_scores_app_output_without_filesystem_staging(tmp_path: Path):
    repo_root = tmp_path / "repo"
    task_rel = "application/tasks/fake-task"
    _write_fake_task(repo_root, task_rel, artifact_source="/app/output")

    trial_dir = tmp_path / "trial"
    _write_trial(
        trial_dir,
        task_rel,
        artifact_source="/app/output",
        with_decision=True,
        with_exception=True,
    )

    ran = maybe_run_host_verifier(repo_root=repo_root, trial_dir=trial_dir)
    assert ran is True
    assert (trial_dir / "verifier" / "reward.txt").read_text(encoding="utf-8").strip() == "1"


def test_host_verifier_scores_trial_and_clears_stale_exception(tmp_path: Path):
    stage_root = Path(tempfile.mkdtemp(prefix="matraix-host-verifier-test-"))
    artifact_source = _artifact_source(stage_root)
    try:
        repo_root = tmp_path / "repo"
        task_rel = "application/tasks/fake-task"
        _write_fake_task(repo_root, task_rel, artifact_source=artifact_source)

        trial_dir = tmp_path / "trial"
        _write_trial(
            trial_dir,
            task_rel,
            artifact_source=artifact_source,
            with_decision=True,
            with_exception=True,
        )

        ran = maybe_run_host_verifier(repo_root=repo_root, trial_dir=trial_dir)

        assert ran is True
        assert (trial_dir / "verifier" / "reward.txt").read_text(encoding="utf-8").strip() == "1"
        assert (trial_dir / "verifier" / "structured_output.json").is_file()

        result = json.loads((trial_dir / "result.json").read_text(encoding="utf-8"))
        assert result["exception_info"] is None
        assert result["verifier_result"] == {"rewards": {"reward": 1.0}}
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)


def test_host_verifier_skips_when_reward_already_present(tmp_path: Path):
    stage_root = Path(tempfile.mkdtemp(prefix="matraix-host-verifier-test-"))
    artifact_source = _artifact_source(stage_root)
    try:
        repo_root = tmp_path / "repo"
        task_rel = "application/tasks/fake-task"
        _write_fake_task(repo_root, task_rel, artifact_source=artifact_source)

        trial_dir = tmp_path / "trial"
        _write_trial(
            trial_dir,
            task_rel,
            artifact_source=artifact_source,
            with_decision=True,
            with_exception=True,
        )
        verifier_dir = trial_dir / "verifier"
        verifier_dir.mkdir(parents=True, exist_ok=True)
        (verifier_dir / "reward.txt").write_text("1", encoding="utf-8")

        ran = maybe_run_host_verifier(repo_root=repo_root, trial_dir=trial_dir)
        assert ran is False
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)


def test_host_verifier_rescues_zero_reward_from_trajectory(tmp_path: Path):
    """Sandbox reward=0 from a missing file can be fixed from the agent trajectory."""
    repo_root = tmp_path / "repo"
    task_rel = "application/tasks/fake-os-app"
    _write_fake_task(repo_root, task_rel, artifact_source="/app/output")

    trial_dir = tmp_path / "trial"
    _write_trial(
        trial_dir,
        task_rel,
        artifact_source="/app/output",
        with_decision=False,
        with_exception=False,
    )
    # Sandbox already wrote a failing reward.
    verifier_dir = trial_dir / "verifier"
    verifier_dir.mkdir(parents=True, exist_ok=True)
    (verifier_dir / "reward.txt").write_text("0", encoding="utf-8")
    (verifier_dir / "test-stdout.txt").write_text(
        "missing /Users/lume/output/decision.json\n", encoding="utf-8"
    )
    (trial_dir / "result.json").write_text(
        json.dumps({"verifier_result": {"rewards": {"reward": 0.0}}}),
        encoding="utf-8",
    )

    agent_dir = trial_dir / "agent"
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "trajectory.json").write_text(
        json.dumps(
            {
                "steps": [
                    {"step_id": 1, "message": "browsing"},
                    {
                        "step_id": 2,
                        "message": '{\n  "clicked": true\n}',
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    (agent_dir / "final_answer.txt").write_text(
        '{\n  "clicked": true\n}', encoding="utf-8"
    )

    ran = maybe_run_host_verifier(repo_root=repo_root, trial_dir=trial_dir)
    assert ran is True
    output_dir = trial_dir / "artifacts" / "app" / "output"
    assert (output_dir / "decision.json").is_file()
    assert (output_dir / "trajectory.json").is_file()
    assert (output_dir / "final_answer.txt").is_file()
    assert (verifier_dir / "reward.txt").read_text(encoding="utf-8").strip() == "1"
    result = json.loads((trial_dir / "result.json").read_text(encoding="utf-8"))
    assert result["verifier_result"] == {"rewards": {"reward": 1.0}}


def test_host_verifier_mirrors_trajectory_even_without_declared_json_artifact(
    tmp_path: Path,
):
    """Persona-style test.sh may not declare OUTPUT_DIR/\"*.json\"; still mirror CUA logs."""
    repo_root = tmp_path / "repo"
    task_rel = "persona/validation/tasks/fake-os-app"
    task_dir = repo_root / task_rel
    (task_dir / "tests").mkdir(parents=True, exist_ok=True)
    (task_dir / "task.toml").write_text(
        'artifacts = ["/app/output"]\n[verifier]\ntimeout_sec = 30.0\n',
        encoding="utf-8",
    )
    (task_dir / "tests" / "test.sh").write_text(
        """\
#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PY'
import os
from pathlib import Path
OUTPUT_DIR = Path(os.environ["PLAYGROUND_OUTPUT_DIR"])
assert (OUTPUT_DIR / "trajectory.json").is_file()
assert (OUTPUT_DIR / "final_answer.txt").is_file()
verifier_dir = Path(os.environ["HARBOR_VERIFIER_DIR"])
verifier_dir.mkdir(parents=True, exist_ok=True)
(verifier_dir / "reward.txt").write_text("1")
PY
""",
        encoding="utf-8",
    )

    trial_dir = tmp_path / "trial"
    trial_dir.mkdir(parents=True, exist_ok=True)
    (trial_dir / "config.json").write_text(
        json.dumps({"task": {"path": task_rel}}), encoding="utf-8"
    )
    (trial_dir / "result.json").write_text("{}", encoding="utf-8")
    agent_dir = trial_dir / "agent"
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "trajectory.json").write_text(
        json.dumps({"steps": [{"message": "done"}]}), encoding="utf-8"
    )
    (agent_dir / "final_answer.txt").write_text("done", encoding="utf-8")

    ran = maybe_run_host_verifier(repo_root=repo_root, trial_dir=trial_dir)
    assert ran is True
    output_dir = trial_dir / "artifacts" / "app" / "output"
    assert (output_dir / "trajectory.json").is_file()
    assert (output_dir / "final_answer.txt").is_file()
    assert (trial_dir / "verifier" / "reward.txt").read_text(encoding="utf-8").strip() == "1"


def test_parse_json_object_uses_first_balanced_object_when_agent_keeps_talking():
    from playground.host_verifier import _parse_json_object

    text = (
        'Here is my answer:\n'
        '```json\n'
        '{\n'
        '  "ticker": "MU",\n'
        '  "sentiment": "buy",\n'
        '  "confidence": 7\n'
        '}\n'
        '```\n\n'
        'Wait, let me reconsider...\n'
        '```json\n'
        '{\n'
        '  "ticker": "MU",\n'
        '  "sentiment": "hold",\n'
        '  "confidence": 4\n'
        '}\n'
        '```\n'
    )
    parsed = _parse_json_object(text)
    assert parsed == {"ticker": "MU", "sentiment": "buy", "confidence": 7}


def test_host_verifier_materializes_when_trajectory_has_trailing_second_json(
    tmp_path: Path,
):
    repo_root = tmp_path / "repo"
    task_rel = "application/tasks/fake-os-app"
    _write_fake_task(repo_root, task_rel, artifact_source="/app/output")

    trial_dir = tmp_path / "trial"
    _write_trial(
        trial_dir,
        task_rel,
        artifact_source="/app/output",
        with_decision=False,
        with_exception=False,
    )
    agent_dir = trial_dir / "agent"
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "trajectory.json").write_text(
        json.dumps(
            {
                "steps": [
                    {
                        "step_id": 1,
                        "message": (
                            '{\n  "clicked": true\n}\n'
                            "```\n\nWait, double-checking...\n"
                            '```json\n{\n  "clicked": false\n}\n```'
                        ),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    ran = maybe_run_host_verifier(repo_root=repo_root, trial_dir=trial_dir)
    assert ran is True
    decision = json.loads(
        (trial_dir / "artifacts" / "app" / "output" / "decision.json").read_text(
            encoding="utf-8"
        )
    )
    assert decision == {"clicked": True}


def test_host_verifier_mirror_alone_does_not_rescue_zero_reward(tmp_path: Path):
    """Trajectory mirror is additive; reward=0 only retries after JSON recovery."""
    repo_root = tmp_path / "repo"
    task_rel = "persona/validation/tasks/fake-os-app-linux"
    task_dir = repo_root / task_rel
    (task_dir / "tests").mkdir(parents=True, exist_ok=True)
    (task_dir / "task.toml").write_text(
        'artifacts = ["/app/output"]\n[verifier]\ntimeout_sec = 30.0\n',
        encoding="utf-8",
    )
    # No OUTPUT_DIR/"….json" declaration — mirror only.
    (task_dir / "tests" / "test.sh").write_text(
        """\
#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PY'
import os
from pathlib import Path
verifier_dir = Path(os.environ["HARBOR_VERIFIER_DIR"])
verifier_dir.mkdir(parents=True, exist_ok=True)
(verifier_dir / "reward.txt").write_text("1")
PY
""",
        encoding="utf-8",
    )

    trial_dir = tmp_path / "trial"
    trial_dir.mkdir(parents=True, exist_ok=True)
    (trial_dir / "config.json").write_text(
        json.dumps({"task": {"path": task_rel}}), encoding="utf-8"
    )
    (trial_dir / "result.json").write_text(
        json.dumps({"verifier_result": {"rewards": {"reward": 0.0}}}),
        encoding="utf-8",
    )
    out = trial_dir / "artifacts" / "app" / "output"
    out.mkdir(parents=True, exist_ok=True)
    (out / "solution.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    verifier_dir = trial_dir / "verifier"
    verifier_dir.mkdir(parents=True, exist_ok=True)
    (verifier_dir / "reward.txt").write_text("0", encoding="utf-8")
    agent_dir = trial_dir / "agent"
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "trajectory.json").write_text('{"steps":[]}', encoding="utf-8")
    (agent_dir / "final_answer.txt").write_text("done", encoding="utf-8")

    ran = maybe_run_host_verifier(repo_root=repo_root, trial_dir=trial_dir)
    assert ran is False
    assert (verifier_dir / "reward.txt").read_text(encoding="utf-8").strip() == "0"
    # Signals still mirrored for task-local / offline use.
    assert (out / "trajectory.json").is_file()
    assert (out / "final_answer.txt").is_file()


def test_host_verifier_skips_zero_reward_without_recoverable_submission(tmp_path: Path):
    repo_root = tmp_path / "repo"
    task_rel = "application/tasks/fake-os-app"
    _write_fake_task(repo_root, task_rel, artifact_source="/app/output")

    trial_dir = tmp_path / "trial"
    _write_trial(
        trial_dir,
        task_rel,
        artifact_source="/app/output",
        with_decision=False,
        with_exception=False,
    )
    verifier_dir = trial_dir / "verifier"
    verifier_dir.mkdir(parents=True, exist_ok=True)
    (verifier_dir / "reward.txt").write_text("0", encoding="utf-8")

    ran = maybe_run_host_verifier(repo_root=repo_root, trial_dir=trial_dir)
    assert ran is False
    assert (verifier_dir / "reward.txt").read_text(encoding="utf-8").strip() == "0"


def test_host_verifier_skips_when_nothing_was_submitted(tmp_path: Path):
    stage_root = Path(tempfile.mkdtemp(prefix="matraix-host-verifier-test-"))
    artifact_source = _artifact_source(stage_root)
    try:
        repo_root = tmp_path / "repo"
        task_rel = "application/tasks/fake-task"
        _write_fake_task(repo_root, task_rel, artifact_source=artifact_source)

        trial_dir = tmp_path / "trial"
        _write_trial(
            trial_dir,
            task_rel,
            artifact_source=artifact_source,
            with_decision=False,
            with_exception=True,
        )

        ran = maybe_run_host_verifier(repo_root=repo_root, trial_dir=trial_dir)
        assert ran is False
        result = json.loads((trial_dir / "result.json").read_text(encoding="utf-8"))
        assert result["exception_info"] is not None
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)


def test_host_verifier_restores_pre_existing_source_contents(tmp_path: Path):
    stage_root = Path(tempfile.mkdtemp(prefix="matraix-host-verifier-test-"))
    artifact_source = _artifact_source(stage_root)
    try:
        repo_root = tmp_path / "repo"
        task_rel = "application/tasks/fake-task"
        _write_fake_task(repo_root, task_rel, artifact_source=artifact_source)

        trial_dir = tmp_path / "trial"
        _write_trial(
            trial_dir,
            task_rel,
            artifact_source=artifact_source,
            with_decision=True,
            with_exception=True,
        )

        stray = Path(artifact_source)
        stray.mkdir(parents=True, exist_ok=True)
        sentinel = stray / "unrelated-concurrent-file.txt"
        sentinel.write_text("keep-me", encoding="utf-8")

        ran = maybe_run_host_verifier(repo_root=repo_root, trial_dir=trial_dir)
        assert ran is True
        assert sentinel.is_file()
        assert sentinel.read_text(encoding="utf-8") == "keep-me"
        assert not (stray / "decision.json").is_file()
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)
