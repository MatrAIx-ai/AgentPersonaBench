"""Score an OS-app trial on the Playground host from downloaded artifacts.

For **use-computer** (macOS/iOS) jobs, Playground disables the in-sandbox
verifier (remote path remap is flaky). The primary host scoring path is
**per-trial**: as soon as a trial writes ``result.json``, Playground runs
this module against host artifacts / ``final_answer.txt`` / trajectory.
A job-end sweep remains as **rescue** for anything the watcher missed.

Harbor may still run ``tests/test.sh`` inside Docker computer-use sandboxes
(mounted paths). This module also rescues when a sandbox left no reward or
scored ``0`` despite a recoverable host-side submission.

Artifact source paths and timeouts come from the task's ``task.toml``; the
host path under ``trial/artifacts/`` follows Harbor's
``source_relative_path`` mapping. Before running ``tests/test.sh``, this module
mirrors ``trajectory.json`` / ``final_answer.txt`` into
``artifacts/app/output/`` (task-agnostic) and, when ``test.sh`` declares a
primary JSON hand-in, recovers that object from agent logs too.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tomllib
import uuid
from pathlib import Path, PurePosixPath
from threading import Lock

_LOCKS: dict[str, Lock] = {}
_LOCKS_GUARD = Lock()

_REWARD_FILENAMES = ("reward.txt", "reward.json")
_MISSING_REWARD_EXCEPTION = "RewardFileNotFoundError"
_DEFAULT_TIMEOUT_SEC = 120.0
_OUTPUT_ARTIFACT_RE = re.compile(
    r"""OUTPUT_DIR\s*/\s*["']([^"']+\.json)["']"""
)
_SKIP_OUTPUT_ARTIFACTS = frozenset({"user_feedback.json", "trajectory.json"})


def _lock_for(key: str) -> Lock:
    with _LOCKS_GUARD:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = Lock()
            _LOCKS[key] = lock
        return lock


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def source_relative_path(source: str) -> PurePosixPath:
    """Map a container artifact source to its path under ``trial/artifacts/``.

    Mirrors Harbor's ``harbor.models.task.artifacts.source_relative_path`` so
    host scoring looks in the same place downloads landed.
    """
    parts = [
        part for part in PurePosixPath(source).parts if part not in ("", "/", "..")
    ]
    return PurePosixPath(*parts) if parts else PurePosixPath(".")


def _is_absolute_source(path: str) -> bool:
    return path.startswith("/") or (len(path) >= 3 and path[1] == ":" and path[0].isalpha())


def _task_path_from_trial(trial_dir: Path) -> str | None:
    config_path = trial_dir / "config.json"
    if not config_path.is_file():
        return None
    try:
        payload = _read_json(config_path)
    except Exception:  # noqa: BLE001
        return None
    task = payload.get("task") if isinstance(payload, dict) else None
    if isinstance(task, dict):
        path = task.get("path")
        if isinstance(path, str) and path.strip():
            return path.strip()
    return None


def _load_task_toml(repo_root: Path, task_path: str) -> dict | None:
    toml_path = repo_root / task_path / "task.toml"
    if not toml_path.is_file():
        return None
    try:
        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    return data if isinstance(data, dict) else None


def _artifact_sources(task_data: dict) -> list[str]:
    artifacts = task_data.get("artifacts")
    if not isinstance(artifacts, list):
        return []
    sources: list[str] = []
    for entry in artifacts:
        source = entry.get("source") if isinstance(entry, dict) else entry
        if isinstance(source, str) and source.strip() and _is_absolute_source(source.strip()):
            sources.append(source.strip())
    return sources


def _verifier_timeout_sec(task_data: dict) -> float:
    verifier = task_data.get("verifier")
    if isinstance(verifier, dict):
        raw = verifier.get("timeout_sec")
        if isinstance(raw, (int, float)) and raw > 0:
            return float(raw)
    return _DEFAULT_TIMEOUT_SEC


def _exception_type(trial_dir: Path) -> str | None:
    result_path = trial_dir / "result.json"
    if not result_path.is_file():
        return None
    try:
        payload = _read_json(result_path)
    except Exception:  # noqa: BLE001
        return None
    exc = payload.get("exception_info") if isinstance(payload, dict) else None
    if isinstance(exc, dict):
        exc_type = exc.get("exception_type")
        if isinstance(exc_type, str):
            return exc_type
    return None


def _read_reward_value(verifier_dir: Path) -> float | None:
    json_path = verifier_dir / "reward.json"
    if json_path.is_file() and json_path.stat().st_size > 0:
        try:
            payload = _read_json(json_path)
            reward = payload.get("reward") if isinstance(payload, dict) else None
            if isinstance(reward, (int, float)):
                return float(reward)
        except Exception:  # noqa: BLE001
            return None
    text_path = verifier_dir / "reward.txt"
    if text_path.is_file() and text_path.stat().st_size > 0:
        try:
            return float(text_path.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            return None
    return None


def _dir_has_files(path: Path) -> bool:
    if not path.is_dir():
        return False
    return any(candidate.is_file() for candidate in path.rglob("*"))


def _downloaded_artifact_dir(trial_dir: Path, source: str) -> Path:
    return trial_dir / "artifacts" / Path(source_relative_path(source))


def _expected_output_artifacts(task_dir: Path) -> list[str]:
    """Primary submission filenames declared by ``tests/test.sh``."""
    test_sh = task_dir / "tests" / "test.sh"
    if not test_sh.is_file():
        return []
    names = _OUTPUT_ARTIFACT_RE.findall(
        test_sh.read_text(encoding="utf-8", errors="replace")
    )
    ordered: list[str] = []
    for name in names:
        if name in _SKIP_OUTPUT_ARTIFACTS or name in ordered:
            continue
        ordered.append(name)
    return ordered


def _first_balanced_json_object(text: str) -> str | None:
    """Return the first top-level ``{...}`` span, respecting strings/escapes.

    A greedy ``\\{[\\s\\S]*\\}`` match fails when the agent emits a valid JSON
    object and then keeps talking (or prints a second JSON block). Prefer the
    first balanced object so trailing commentary does not poison ``json.loads``.
    """
    if not text:
        return None
    start = -1
    depth = 0
    in_string = False
    escape = False
    for index, char in enumerate(text):
        if escape:
            escape = False
            continue
        if in_string:
            if char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}":
            if depth == 0:
                continue
            depth -= 1
            if depth == 0 and start != -1:
                return text[start : index + 1]
    return None


def _parse_json_object(text: str) -> dict | None:
    candidate = _first_balanced_json_object(text or "")
    if candidate is None:
        return None
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _extract_submission_from_agent_logs(trial_dir: Path) -> dict | None:
    agent_dir = trial_dir / "agent"
    final_answer = agent_dir / "final_answer.txt"
    if final_answer.is_file():
        parsed = _parse_json_object(
            final_answer.read_text(encoding="utf-8", errors="replace")
        )
        if parsed is not None:
            return parsed

    trajectory_path = agent_dir / "trajectory.json"
    if not trajectory_path.is_file():
        return None
    try:
        trajectory = _read_json(trajectory_path)
    except Exception:  # noqa: BLE001
        return None
    steps = trajectory.get("steps") if isinstance(trajectory, dict) else None
    if not isinstance(steps, list):
        return None
    for step in reversed(steps):
        if not isinstance(step, dict):
            continue
        message = step.get("message")
        if not isinstance(message, str):
            continue
        parsed = _parse_json_object(message)
        if parsed is not None:
            return parsed
    return None


def _mirror_agent_log_file(
    *, agent_dir: Path, output_dir: Path, name: str
) -> bool:
    """Copy ``agent/<name>`` into downloaded ``/app/output`` when missing."""
    src = agent_dir / name
    dst = output_dir / name
    if not src.is_file() or dst.is_file():
        return False
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    except OSError:
        return False
    return True


def _materialize_output_from_agent_logs(
    *, trial_dir: Path, task_dir: Path, sources: list[str]
) -> bool:
    """Materialize agent logs into downloaded ``/app/output``.

    Always mirrors ``trajectory.json`` / ``final_answer.txt`` when present so
    task-local ``tests/test.sh`` can read CUA signals on the host (additive,
    task-agnostic). Additionally recovers a primary JSON hand-in into filenames
    declared by ``test.sh``.

    Returns ``True`` only when a **primary JSON** artifact was newly recovered.
    Signal mirroring alone does not count — otherwise every ``reward=0`` trial
    with a trajectory would be re-scored (and can flip to a false pass when the
    host lacks persona/probe context).
    """
    output_sources = [source for source in sources if source.rstrip("/") == "/app/output"]
    if not output_sources:
        return False

    output_dir = _downloaded_artifact_dir(trial_dir, "/app/output")
    agent_dir = trial_dir / "agent"

    # Task-agnostic CUA signals — available to every task's host verifier.
    for name in ("trajectory.json", "final_answer.txt"):
        _mirror_agent_log_file(agent_dir=agent_dir, output_dir=output_dir, name=name)

    # Named JSON hand-in recovery (declared by test.sh via OUTPUT_DIR/"….json").
    artifact_names = _expected_output_artifacts(task_dir)
    missing = [name for name in artifact_names if not (output_dir / name).is_file()]
    if not missing:
        return False

    payload = _extract_submission_from_agent_logs(trial_dir)
    if payload is None:
        return False

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        # One hand-in JSON becomes the first missing primary artifact.
        target = output_dir / missing[0]
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        return False
    return True


def _prepare_host_scoring(
    trial_dir: Path, sources: list[str]
) -> tuple[list[tuple[str, Path]], dict[str, str]] | None:
    """Return filesystem staging pairs and env overrides for host ``test.sh``."""
    stage_pairs: list[tuple[str, Path]] = []
    env_overrides: dict[str, str] = {}
    saw_artifacts = False

    for source in sources:
        downloaded = _downloaded_artifact_dir(trial_dir, source)
        if not _dir_has_files(downloaded):
            continue
        saw_artifacts = True
        if source.rstrip("/") == "/app/output":
            output_dir = str(downloaded)
            env_overrides["PLAYGROUND_OUTPUT_DIR"] = output_dir
            env_overrides["MATRIX_OUTPUT_DIR"] = output_dir
            env_overrides["HARBOR_OUTPUT_DIR"] = output_dir
            continue
        staged = Path(source)
        parent = staged.parent
        try:
            parent.mkdir(parents=True, exist_ok=True)
            probe = parent / f".matraix-host-verifier-probe-{uuid.uuid4().hex}"
            probe.write_text("", encoding="utf-8")
            probe.unlink(missing_ok=True)
        except OSError:
            continue
        stage_pairs.append((source, downloaded))

    if not saw_artifacts:
        return None
    return stage_pairs, env_overrides


def _stage_sources(pairs: list[tuple[str, Path]]) -> list[tuple[Path, Path | None]]:
    """Copy downloaded artifacts onto their declared absolute sources.

    Returns a list of ``(staged_root, backup_dir_or_none)`` for restore.
    """
    staged: list[tuple[Path, Path | None]] = []
    try:
        for source, downloaded in pairs:
            staged_root = Path(source)
            backup_dir: Path | None = None
            if staged_root.exists() or staged_root.is_symlink():
                backup_dir = staged_root.with_name(
                    staged_root.name
                    + f".matraix-host-verifier-{uuid.uuid4().hex}.bak"
                )
                shutil.rmtree(backup_dir, ignore_errors=True)
                shutil.move(str(staged_root), str(backup_dir))
            shutil.copytree(downloaded, staged_root)
            staged.append((staged_root, backup_dir))
    except Exception:
        _restore_staged(staged)
        raise
    return staged


def _restore_staged(staged: list[tuple[Path, Path | None]]) -> None:
    for staged_root, backup_dir in reversed(staged):
        shutil.rmtree(staged_root, ignore_errors=True)
        if backup_dir is not None:
            shutil.move(str(backup_dir), str(staged_root))


def _write_trial_verifier_result(trial_dir: Path, reward: float) -> None:
    """Persist host scoring into ``result.json`` (and clear stale verifier errors)."""
    result_path = trial_dir / "result.json"
    if not result_path.is_file():
        return
    try:
        payload = _read_json(result_path)
    except Exception:  # noqa: BLE001
        return
    if not isinstance(payload, dict):
        return
    exc = payload.get("exception_info")
    if isinstance(exc, dict) and exc.get("exception_type") == _MISSING_REWARD_EXCEPTION:
        payload["exception_info"] = None
    payload["verifier_result"] = {"rewards": {"reward": reward}}
    try:
        result_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass


def _should_run_host_verifier(trial_dir: Path, *, materialized: bool) -> bool:
    """Host-score when sandbox left no reward, or reward=0 after we recovered a file."""
    reward = _read_reward_value(trial_dir / "verifier")
    if reward is None:
        return True
    if reward > 0:
        return False
    # Sandbox scored 0 — only retry on host when we newly recovered a submission.
    return materialized


def maybe_run_host_verifier(
    *, repo_root: Path, trial_dir: Path, timeout_sec: float | None = None
) -> bool:
    """Run the task verifier on this host against downloaded trial artifacts.

    Returns ``True`` when a host verifier run happened, ``False`` when it was
    skipped (already passed, nothing to score, no test script, etc.).
    """
    task_path = _task_path_from_trial(trial_dir)
    if not task_path:
        return False

    task_data = _load_task_toml(repo_root, task_path)
    if task_data is None:
        return False

    task_dir = repo_root / task_path
    test_sh = task_dir / "tests" / "test.sh"
    if not test_sh.is_file():
        return False

    sources = _artifact_sources(task_data)
    if not sources:
        return False

    materialized = _materialize_output_from_agent_logs(
        trial_dir=trial_dir, task_dir=task_dir, sources=sources
    )
    if not _should_run_host_verifier(trial_dir, materialized=materialized):
        return False

    pairs = _prepare_host_scoring(trial_dir, sources)
    if pairs is None:
        return False
    stage_pairs, env_overrides = pairs
    if not stage_pairs and not env_overrides.get("PLAYGROUND_OUTPUT_DIR"):
        return False

    verifier_dir = trial_dir / "verifier"
    verifier_dir.mkdir(parents=True, exist_ok=True)
    effective_timeout = (
        timeout_sec if timeout_sec is not None else _verifier_timeout_sec(task_data)
    )

    lock_keys = [source for source, _ in stage_pairs] or ["/app/output"]
    locks = [_lock_for(key) for key in lock_keys]
    for lock in locks:
        lock.acquire()
    stdout_text = ""
    try:
        staged = _stage_sources(stage_pairs)
        try:
            env = dict(os.environ)
            env["HARBOR_VERIFIER_DIR"] = str(verifier_dir)
            env.update(env_overrides)
            try:
                completed = subprocess.run(
                    ["bash", str(test_sh)],
                    cwd=task_dir / "tests",
                    env=env,
                    timeout=effective_timeout,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                stdout_text = (completed.stdout or "") + (completed.stderr or "")
            except subprocess.TimeoutExpired as exc:
                stdout_text = (
                    f"host verifier timed out after {effective_timeout}s\n"
                    f"{exc.stdout or ''}{exc.stderr or ''}"
                )
        finally:
            _restore_staged(staged)
    finally:
        for lock in reversed(locks):
            lock.release()

    stdout_path = verifier_dir / "test-stdout.txt"
    if stdout_text.strip():
        try:
            stdout_path.write_text(stdout_text, encoding="utf-8")
        except OSError:
            pass

    reward = _read_reward_value(verifier_dir)
    if reward is not None:
        _write_trial_verifier_result(trial_dir, reward)

    return True
