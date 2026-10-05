#!/usr/bin/env python3
"""Run a reproducible PersonaBench evaluation suite with concurrency and resume.

The suite runner discovers merged task leaves, runs task_doctor before spending API
credits, executes seeds sequentially per task/model (avoiding trial-directory races),
and writes an append-only suite manifest under evaluation/results/suites/.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVALUATION = REPO / "evaluation"
TASK_ROOTS = {
    "single-attribute": REPO / "tasks" / "single-attribute",
    "multi-attribute": REPO / "tasks" / "multi-attribute",
}
SUITES = EVALUATION / "results" / "suites"
_FINAL_STATUSES = {"pass", "fail", "error", "timeout", "preflight_error"}
_EVENT_LOCK = threading.Lock()
def _openai_compatible_provider_keys() -> dict[str, tuple[str, ...]]:
    """Key env vars for the OpenAI-compatible providers, from the one registry.

    Imported lazily from evaluation/src so a new compatible provider (Qwen, GLM, a
    local gateway) becomes selectable here without editing this file, and so the
    suite runner still imports cleanly when evaluation/src is not on the path.
    """
    try:
        sys.path.insert(0, str(EVALUATION / "src"))
        import openai_compat
    except ImportError:  # pragma: no cover - falls back to the built-in set
        return {"openai": ("OPENAI_API_KEY",)}
    return {name: tuple(spec.key_env) for name, spec in openai_compat.REGISTRY.items()}


_PROVIDER_KEYS = {
    "anthropic": ("ANTHROPIC_API_KEY",),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    **_openai_compatible_provider_keys(),
}


class Progress:
    """Thread-safe dependency-free terminal progress display."""

    def __init__(self, label: str, total: int) -> None:
        self.label = label
        self.total = total
        self.completed = 0
        self.started = time.monotonic()
        self.counts: dict[str, int] = {}
        self._lock = threading.Lock()
        self._interactive = sys.stderr.isatty()
        self._last_width = 0
        self._render(force=True)

    @staticmethod
    def _duration(seconds: float) -> str:
        seconds = max(0, round(seconds))
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:d}:{minutes:02d}:{seconds:02d}"

    def _render(self, force: bool = False) -> None:
        if not self._interactive and not force and self.completed not in {self.total}:
            interval = max(1, self.total // 100)
            if self.completed % interval:
                return
        elapsed = time.monotonic() - self.started
        rate = self.completed / elapsed if elapsed > 0 else 0
        eta = (self.total - self.completed) / rate if rate > 0 else 0
        fraction = self.completed / self.total if self.total else 1
        width = 24
        filled = min(width, round(width * fraction))
        bar = "#" * filled + "-" * (width - filled)
        statuses = " ".join(f"{key}={value}" for key, value in sorted(self.counts.items()))
        line = (
            f"{self.label} [{bar}] {self.completed}/{self.total} ({fraction:6.1%}) "
            f"elapsed {self._duration(elapsed)} ETA {self._duration(eta)}"
        )
        if statuses:
            line += f" | {statuses}"
        if self._interactive:
            padding = " " * max(0, self._last_width - len(line))
            print(f"\r{line}{padding}", end="", file=sys.stderr, flush=True)
            self._last_width = len(line)
        else:
            print(line, file=sys.stderr, flush=True)

    def advance(self, status: str) -> None:
        with self._lock:
            self.completed += 1
            self.counts[status] = self.counts.get(status, 0) + 1
            self._render()

    def finish(self) -> None:
        with self._lock:
            self._render(force=True)
            if self._interactive:
                print(file=sys.stderr, flush=True)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def discover_tasks(patterns: list[str] | None = None, surfaces: set[str] | None = None) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for bucket, root in TASK_ROOTS.items():
        for manifest in sorted(root.rglob("task.toml")):
            relative = manifest.parent.relative_to(root).as_posix()
            try:
                meta = tomllib.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
                tasks.append({"bucket": bucket, "task": relative, "surface": "unknown", "manifest_error": str(exc)})
                continue
            task_meta = meta.get("task") or {}
            metadata = meta.get("metadata") or {}
            surface = str(metadata.get("type") or relative.rsplit("-", 1)[-1]).lower()
            candidate = f"{bucket}/{relative}"
            if patterns and not any(fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(candidate, pattern) for pattern in patterns):
                continue
            if surfaces and surface not in surfaces:
                continue
            checks = meta.get("checks") or []
            tasks.append({
                "bucket": bucket,
                "task": relative,
                "surface": surface,
                "name": task_meta.get("name"),
                "theme": task_meta.get("theme"),
                "checks": len(checks),
                # a judge call happens at verify time, long after the arm has been
                # paid for, so preflight has to know whether one is coming
                "needs_judge": any(c.get("evaluator") == "llm-judge" for c in checks),
            })
    return tasks


def run_preflight(task: dict[str, Any], python: str) -> dict[str, Any]:
    if task.get("manifest_error"):
        return {"status": "fail", "returncode": 2, "detail": task["manifest_error"]}
    proc = subprocess.run(
        [python, str(EVALUATION / "src" / "tools" / "task_doctor.py"), task["task"]],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )
    output = (proc.stdout + "\n" + proc.stderr).strip()
    return {
        "status": "pass" if proc.returncode == 0 else "fail",
        "returncode": proc.returncode,
        "detail": output[-4000:],
    }


def run_preflights(tasks: list[dict[str, Any]], python: str, workers: int) -> dict[str, dict[str, Any]]:
    progress = Progress("Preflight", len(tasks))
    results: dict[str, dict[str, Any]] = {}
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(run_preflight, task, python): task for task in tasks}
            for future in concurrent.futures.as_completed(futures):
                task = futures[future]
                result = future.result()
                results[task["task"]] = result
                progress.advance(result["status"])
    finally:
        progress.finish()
    return results


def load_arm_configs(models: list[str], model_ids: dict[str, str]) -> dict[str, dict[str, Any]]:
    configs: dict[str, dict[str, Any]] = {}
    for arm in models:
        path = EVALUATION / "configs" / f"{arm}.json"
        if not path.is_file():
            raise SystemExit(f"error: missing arm config {path.relative_to(REPO)}")
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"error: invalid arm config {path.relative_to(REPO)}: {exc}") from exc
        if not isinstance(config, dict) or not isinstance(config.get("model"), str):
            raise SystemExit(f"error: arm config {path.relative_to(REPO)} must contain a string model")
        provider = config.get("provider")
        if provider not in _PROVIDER_KEYS:
            raise SystemExit(f"error: unsupported provider {provider!r} in {path.relative_to(REPO)}")
        config = dict(config)
        if arm in model_ids:
            config["model"] = model_ids[arm]
            config["model_overridden"] = True
        configs[arm] = config
    unknown = set(model_ids) - set(models)
    if unknown:
        raise SystemExit(f"error: --model-id specified for unselected arm(s): {', '.join(sorted(unknown))}")
    return configs


def validate_resolved_models(configs: dict[str, dict[str, Any]]) -> None:
    unresolved = [arm for arm, config in configs.items()
                  if str(config.get("model", "")).startswith("REPLACE_WITH_")]
    if unresolved:
        arms = ", ".join(sorted(unresolved))
        raise SystemExit(f"error: unresolved provider model id for arm(s): {arms}; use --model-id ARM=MODEL_ID")


def _vertex_adc_ready(provider: str) -> bool:
    """Gemini on Vertex AI authenticates with application-default credentials
    (`gcloud auth application-default login`), not a key."""
    if provider != "gemini" or (os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") or "").strip().lower() not in ("1", "true", "yes"):
        return False
    adc = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.path.expanduser(
        "~/.config/gcloud/application_default_credentials.json")
    return os.path.isfile(adc)


def runtime_readiness(tasks: list[dict[str, Any]], configs: dict[str, dict[str, Any]], python: str) -> dict[str, Any]:
    credentials = {}
    for arm, config in configs.items():
        provider = str(config["provider"])
        names = _PROVIDER_KEYS[provider]
        configured = any(os.environ.get(name) for name in names) or _vertex_adc_ready(provider)
        credentials[arm] = {
            "provider": provider,
            "configured": configured,
            "accepted_env": list(names),
        }
    # survey belongs here too: a survey task's solve.sh sources harbor_solve.sh, and
    # harbor runs its agent inside a docker-compose environment. Only chat is
    # host-only (chat_harness.py talks to the provider directly from this process).
    # The LLM judge is a second provider, resolved independently of the arm, and
    # it is called at verify time - after a chat trial has spent several minutes.
    # Checking it here is the difference between failing in preflight and failing
    # once per task with the work already paid for.
    if any(task.get("needs_judge") for task in tasks):
        # Resolved by the same module run_task uses, so preflight can never check
        # a different judge than the one that will actually score the run.
        sys.path.insert(0, str(EVALUATION / "src"))
        import judge as judge_config

        for arm, config in configs.items():
            resolved = judge_config.resolve(config, os.environ)
            names = _PROVIDER_KEYS.get(resolved.provider, ())
            credentials[f"{arm} (llm judge)"] = {
                "provider": resolved.provider,
                "model": resolved.model,
                "source": resolved.source,
                "configured": any(os.environ.get(name) for name in names),
                "accepted_env": list(names),
            }

    needs_docker = any(task.get("surface") in {"survey", "web", "app"} for task in tasks)
    docker_cli = shutil.which("docker") is not None
    docker_ready = False
    docker_error = None
    if needs_docker and docker_cli:
        proc = subprocess.run(["docker", "info"], text=True, capture_output=True, check=False, timeout=20)
        docker_ready = proc.returncode == 0
        if not docker_ready:
            docker_error = (proc.stderr or proc.stdout)[-1000:].strip()
    imports = subprocess.run(
        [python, "-c", "import anthropic, yaml"], text=True, capture_output=True, check=False,
    )
    return {
        "python": python,
        "python_ready": imports.returncode == 0,
        "python_error": imports.stderr[-1000:].strip() if imports.returncode else None,
        "docker_required": needs_docker,
        "docker_cli": docker_cli,
        "docker_ready": docker_ready if needs_docker else None,
        "docker_error": docker_error,
        "credentials": credentials,
    }


def parse_model_ids(values: list[str] | None) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values or []:
        arm, separator, model_id = value.partition("=")
        if not separator or not arm or not model_id or arm in result:
            raise SystemExit("error: --model-id must be a unique ARM=PROVIDER_MODEL_ID pair")
        result[arm] = model_id
    return result


def run_key(task: str, model: str, effort: str, seed: int) -> str:
    raw = f"{task}|{model}|{effort}|{seed}"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", raw)


def append_event(path: Path, event: dict[str, Any]) -> None:
    line = json.dumps(event, ensure_ascii=False, sort_keys=True)
    with _EVENT_LOCK:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()


def read_completed(path: Path) -> dict[str, dict[str, Any]]:
    completed: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return completed
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("event") == "completed" and event.get("status") in _FINAL_STATUSES:
            completed[str(event.get("run_key"))] = event
    return completed


def envelope_from_stdout(stdout: str) -> Path | None:
    for line in reversed(stdout.splitlines()):
        match = re.search(r"->\s+(.*/envelope\.json)\s*$", line)
        if match:
            path = REPO / match.group(1)
            if path.is_file():
                return path
    return None


def execute_one(
    task: dict[str, Any], model: str, effort: str, seed: int, suite_id: str,
    python: str, events_path: Path, model_id: str | None = None,
    progress: Progress | None = None,
) -> dict[str, Any]:
    key = run_key(task["task"], model, effort, seed)
    started = utc_now()
    t0 = time.monotonic()
    append_event(events_path, {
        "event": "started", "run_key": key, "task": task["task"], "bucket": task["bucket"],
        "surface": task["surface"], "model": model, "effort": effort, "seed": seed,
        "started_at": started,
    })
    command = [python, str(EVALUATION / "run_task.py"), task["task"], "--model", model,
               "--effort", effort, "--seed", str(seed), "--suite-id", suite_id, "--run-key", key]
    if model_id:
        command.extend(("--model-id", model_id))
    try:
        proc = subprocess.run(
            command,
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        event = {
            "event": "completed", "run_key": key, "task": task["task"], "bucket": task["bucket"],
            "surface": task["surface"], "model": model, "effort": effort, "seed": seed,
            "status": "error", "returncode": None, "reward": None, "score": None,
            "duration_s": round(time.monotonic() - t0, 3), "started_at": started,
            "finished_at": utc_now(), "envelope": None, "stdout_tail": "",
            "stderr_tail": f"failed to launch task runner: {type(exc).__name__}: {exc}",
        }
        append_event(events_path, event)
        if progress:
            progress.advance("error")
        return event
    envelope_path = envelope_from_stdout(proc.stdout)
    envelope: dict[str, Any] = {}
    if envelope_path:
        try:
            envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            envelope = {}
    status = str(envelope.get("status") or ({0: "pass", 1: "fail", 124: "timeout"}.get(proc.returncode, "error")))
    event = {
        "event": "completed", "run_key": key, "task": task["task"], "bucket": task["bucket"],
        "surface": task["surface"], "model": model, "effort": effort, "seed": seed,
        "status": status, "returncode": proc.returncode, "reward": envelope.get("reward"),
        "score": envelope.get("score"), "duration_s": round(time.monotonic() - t0, 3),
        "started_at": started, "finished_at": utc_now(),
        "envelope": envelope_path.relative_to(REPO).as_posix() if envelope_path else None,
        "stdout_tail": proc.stdout[-2000:], "stderr_tail": proc.stderr[-4000:],
    }
    append_event(events_path, event)
    if progress:
        progress.advance(status)
    return event


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", action="append", dest="models", help="arm id; repeat for multiple arms")
    parser.add_argument("--model-id", action="append", metavar="ARM=MODEL_ID",
                        help="override a selected arm's provider model id without editing its config")
    parser.add_argument("--seed", action="append", type=int, dest="seeds", help="repeat for multiple seeds")
    parser.add_argument("--task", action="append", dest="patterns", help="glob matched against task or bucket/task")
    parser.add_argument("--surface", action="append", choices=("survey", "chat", "web", "app"))
    parser.add_argument("--effort", default="medium")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--suite-id", default=None)
    parser.add_argument("--python", default=os.environ.get("RUNTIME_PYTHON") or sys.executable)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--skip-runtime-check", action="store_true",
                        help="allow execution despite missing local credentials/dependencies (not recommended)")
    parser.add_argument("--retry-errors", action="store_true")
    parser.add_argument("--list", action="store_true", help="list selected tasks without running")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.workers < 1:
        raise SystemExit("error: --workers must be at least 1")
    models = args.models or ["opus-4-8"]
    model_ids = parse_model_ids(args.model_id)
    seeds = args.seeds or [0]
    tasks = discover_tasks(args.patterns, set(args.surface or []))
    if not tasks:
        raise SystemExit("error: no tasks matched")
    arm_configs = load_arm_configs(models, model_ids)
    if args.list:
        for task in tasks:
            print(f"{task['bucket']}/{task['task']}\t{task['surface']}")
        return
    if not args.preflight_only:
        validate_resolved_models(arm_configs)

    suite_id = args.suite_id or datetime.now(timezone.utc).strftime("pilot-%Y%m%dT%H%M%SZ")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", suite_id):
        raise SystemExit("error: --suite-id may contain only letters, digits, dot, underscore, and hyphen")
    suite_dir = SUITES / suite_id
    if suite_dir.exists() and not suite_dir.is_dir():
        raise SystemExit(f"error: suite path exists but is not a directory: {suite_dir.relative_to(REPO)}")
    suite_dir.mkdir(parents=True, exist_ok=True)
    events_path = suite_dir / "events.jsonl"
    plan_path = suite_dir / "plan.json"

    preflight = run_preflights(tasks, args.python, args.workers)
    readiness = runtime_readiness(tasks, arm_configs, args.python)
    git_proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, text=True, capture_output=True, check=False)
    if git_proc.returncode != 0:
        raise SystemExit(f"error: cannot resolve repository HEAD: {git_proc.stderr.strip() or 'git failed'}")
    git_sha = git_proc.stdout.strip()
    plan = {
        "schema_version": 1, "suite_id": suite_id, "created_at": utc_now(), "git_sha": git_sha,
        "models": models, "seeds": seeds, "effort": args.effort, "workers": args.workers,
        "arm_configs": arm_configs, "runtime_readiness": readiness,
        "task_patterns": args.patterns or [], "surfaces": args.surface or [], "tasks": tasks,
        "preflight": preflight,
    }
    if plan_path.is_file():
        try:
            previous = json.loads(plan_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"error: cannot read existing suite plan {plan_path.relative_to(REPO)}: {exc}") from exc
        comparable = ("git_sha", "models", "seeds", "effort", "arm_configs", "task_patterns", "surfaces")
        if any(previous.get(key) != plan.get(key) for key in comparable):
            raise SystemExit(f"error: suite {suite_id!r} exists with a different plan")
    else:
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    failed_preflight = [task for task in tasks if preflight[task["task"]]["status"] != "pass"]
    credential_ready = all(item["configured"] for item in readiness["credentials"].values())
    docker_ready = not readiness["docker_required"] or readiness["docker_ready"]
    runtime_ready = readiness["python_ready"] and docker_ready and credential_ready
    print(
        f"Suite {suite_id}: {len(tasks)} tasks, {len(models)} arms, {len(seeds)} seeds; "
        f"preflight {len(tasks) - len(failed_preflight)}/{len(tasks)} passed"
    )
    print(
        f"Runtime readiness: {'PASS' if runtime_ready else 'NOT READY'} "
        f"(python={readiness['python_ready']}, docker={readiness['docker_ready']}, "
        f"credentials={credential_ready})"
    )
    if args.preflight_only:
        for task in failed_preflight:
            print(f"PREFLIGHT_ERROR {task['task']}")
        raise SystemExit(1 if failed_preflight else 0)
    if not runtime_ready and not args.skip_runtime_check:
        raise SystemExit("error: runtime readiness failed; fix plan.json diagnostics or use --skip-runtime-check")

    completed = read_completed(events_path)
    runnable = [task for task in tasks if preflight[task["task"]]["status"] == "pass"]
    for task in failed_preflight:
        for model in models:
            for seed in seeds:
                key = run_key(task["task"], model, args.effort, seed)
                if key not in completed:
                    append_event(events_path, {
                        "event": "completed", "run_key": key, "task": task["task"], "bucket": task["bucket"],
                        "surface": task["surface"], "model": model, "effort": args.effort, "seed": seed,
                        "status": "preflight_error", "returncode": 2, "finished_at": utc_now(),
                        "detail": preflight[task["task"]]["detail"],
                    })

    groups: list[tuple[dict[str, Any], str, list[int]]] = []
    for task in runnable:
        for model in models:
            pending = []
            for seed in seeds:
                previous = completed.get(run_key(task["task"], model, args.effort, seed))
                if previous is None or (args.retry_errors and previous.get("status") in {"error", "timeout"}):
                    pending.append(seed)
            if pending:
                groups.append((task, model, pending))

    def execute_group(group: tuple[dict[str, Any], str, list[int]]) -> list[dict[str, Any]]:
        task, model, pending = group
        override = model_ids.get(model)
        return [execute_one(
            task, model, args.effort, seed, suite_id, args.python, events_path, override, run_progress,
        ) for seed in pending]

    results: list[dict[str, Any]] = []
    run_progress = Progress("Evaluation", sum(len(pending) for _, _, pending in groups))
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            for group_results in pool.map(execute_group, groups):
                results.extend(group_results)
    finally:
        run_progress.finish()

    all_events = read_completed(events_path)
    counts: dict[str, int] = {}
    for event in all_events.values():
        counts[event["status"]] = counts.get(event["status"], 0) + 1
    print("Completed:", ", ".join(f"{key}={value}" for key, value in sorted(counts.items())))
    print(f"Next: {args.python} evaluation/report_suite.py {suite_id}")
    if any(status in counts for status in ("error", "timeout", "preflight_error")):
        raise SystemExit(3)


if __name__ == "__main__":
    main()
