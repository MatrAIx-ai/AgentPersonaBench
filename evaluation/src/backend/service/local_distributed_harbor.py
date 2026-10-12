"""Local distributed coordinator for Playground Harbor auto runs."""

from __future__ import annotations

import json
import shutil
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_str() -> str:
    return _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _json_dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


def _task_name(task_config: dict[str, Any]) -> str:
    raw = str(task_config.get("path") or task_config.get("name") or "trial").strip()
    normalized = raw.replace("\\", "/").rstrip("/")
    return Path(normalized).name or "trial"


def _trial_name(task_config: dict[str, Any]) -> str:
    prefix = _task_name(task_config)[:32].rstrip("_-")
    suffix = uuid.uuid4().hex[:7]
    return f"{prefix or 'trial'}__{suffix}"


def _trial_worker_command(harbor_command: tuple[str, ...], manifest_path: Path) -> list[str]:
    base = list(harbor_command)
    if base and base[-1] == "run":
        base = base[:-1]
    return [*base, "trials", "start", "-c", str(manifest_path)]


def _write_failure_result(trial_dir: Path, config: dict[str, Any], *, exception_type: str, exception_message: str) -> None:
    trial_dir.mkdir(parents=True, exist_ok=True)
    (trial_dir / "config.json").write_text(_json_dump(config), encoding="utf-8")
    payload = {
        "trial_name": config.get("trial_name"),
        "task_name": _task_name(config.get("task") or {}),
        "trial_uri": trial_dir.expanduser().resolve().as_uri(),
        "task_id": {"path": str((config.get("task") or {}).get("path") or "")},
        "source": (config.get("task") or {}).get("source"),
        "task_checksum": "",
        "config": config,
        "agent_info": {
            "name": ((config.get("agent") or {}).get("name") or "unknown"),
            "version": "distributed-worker",
            "model_info": None,
        },
        "exception_info": {
            "exception_type": exception_type,
            "exception_message": exception_message,
            "exception_traceback": "",
            "occurred_at": _utc_now_str(),
        },
        "started_at": _utc_now_str(),
        "finished_at": _utc_now_str(),
    }
    (trial_dir / "result.json").write_text(_json_dump(payload), encoding="utf-8")


@dataclass(frozen=True)
class LocalDistributedTrialManifest:
    trial_name: str
    trial_dir: Path
    manifest_path: Path
    config: dict[str, Any]


@dataclass
class LocalDistributedHarborCoordinator:
    repo_root: Path
    job_name: str
    job_config: dict[str, Any]
    launch_env: dict[str, str]
    command_runner: Callable[..., int]
    harbor_command: tuple[str, ...]
    worker_runner: Callable[[Path, dict[str, str]], int] | None = None
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = field(default_factory=_utc_now)

    @property
    def jobs_dir(self) -> Path:
        raw = Path(str(self.job_config.get("jobs_dir") or "jobs"))
        return raw if raw.is_absolute() else self.repo_root / raw

    @property
    def job_dir(self) -> Path:
        return self.jobs_dir / self.job_name

    @property
    def generated_dir(self) -> Path:
        return self.job_dir / "_generated"

    @property
    def manifests_dir(self) -> Path:
        return self.generated_dir / "distributed_manifests"

    @property
    def state_path(self) -> Path:
        return self.generated_dir / "distributed_state.json"

    def run(self) -> dict[str, Any]:
        self.job_dir.mkdir(parents=True, exist_ok=True)
        self.generated_dir.mkdir(parents=True, exist_ok=True)
        self.manifests_dir.mkdir(parents=True, exist_ok=True)
        (self.job_dir / "config.json").write_text(_json_dump(self.job_config), encoding="utf-8")
        manifests = self._materialize_trial_manifests()
        self._write_state(manifests, status="running", retries=0)
        self._write_job_result(manifests=manifests, retries=0, finished=False)

        retries = 0
        concurrency = int(self.job_config.get("n_concurrent_trials") or 1)
        max_workers = max(1, min(concurrency, len(manifests)))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(self._run_manifest_with_retries, manifest): manifest
                for manifest in manifests
            }
            for future in as_completed(futures):
                retries += int(future.result())
                self._write_state(manifests, status="running", retries=retries)
                self._write_job_result(manifests=manifests, retries=retries, finished=False)

        self._write_state(manifests, status="completed", retries=retries)
        self._write_job_result(manifests=manifests, retries=retries, finished=True)
        return {"trialCount": len(manifests), "retries": retries, "jobDir": str(self.job_dir)}

    def _materialize_trial_manifests(self) -> list[LocalDistributedTrialManifest]:
        manifests: list[LocalDistributedTrialManifest] = []
        for trial_config in self._planned_trial_configs():
            trial_name = str(trial_config["trial_name"])
            trial_dir = self.job_dir / trial_name
            manifest_path = self.manifests_dir / f"{trial_name}.json"
            self._prime_trial_dir(trial_dir, trial_config)
            manifest_path.write_text(_json_dump(trial_config), encoding="utf-8")
            manifests.append(
                LocalDistributedTrialManifest(
                    trial_name=trial_name,
                    trial_dir=trial_dir,
                    manifest_path=manifest_path,
                    config=trial_config,
                )
            )
        return manifests

    def _planned_trial_configs(self) -> list[dict[str, Any]]:
        tasks = list(self.job_config.get("tasks") or [])
        agents = list(self.job_config.get("agents") or [])
        if not tasks:
            raise ValueError("local distributed Harbor requires at least one explicit task")
        if self.job_config.get("datasets"):
            raise ValueError("local distributed Harbor does not support dataset-backed jobs")
        job_id = self.job_id
        payloads: list[dict[str, Any]] = []
        for _ in range(int(self.job_config.get("n_attempts") or 1)):
            for task in tasks:
                for agent in agents:
                    payloads.append(
                        {
                            "task": task,
                            "trial_name": _trial_name(task),
                            "trials_dir": str(self.job_dir),
                            "timeout_multiplier": self.job_config.get("timeout_multiplier", 1.0),
                            "agent_timeout_multiplier": self.job_config.get("agent_timeout_multiplier"),
                            "verifier_timeout_multiplier": self.job_config.get("verifier_timeout_multiplier"),
                            "agent_setup_timeout_multiplier": self.job_config.get("agent_setup_timeout_multiplier"),
                            "environment_build_timeout_multiplier": self.job_config.get("environment_build_timeout_multiplier"),
                            "agent": agent,
                            "environment": self.job_config.get("environment") or {},
                            "verifier": self.job_config.get("verifier") or {},
                            "artifacts": self.job_config.get("artifacts") or [],
                            "extra_instruction_paths": self.job_config.get("extra_instruction_paths") or [],
                            "job_id": job_id,
                        }
                    )
        return payloads

    def _invoke_worker(self, manifest: LocalDistributedTrialManifest) -> int:
        env = dict(self.launch_env)
        env["MATRIX_PLAYGROUND_JOB_NAME"] = self.job_name
        if self.worker_runner is not None:
            return int(self.worker_runner(manifest.manifest_path, env))
        return int(
            self.command_runner(
                _trial_worker_command(self.harbor_command, manifest.manifest_path),
                cwd=self.repo_root,
                env=env,
            )
        )

    def _run_manifest_with_retries(self, manifest: LocalDistributedTrialManifest) -> int:
        retries = 0
        retry = self.job_config.get("retry") or {}
        max_retries = int(retry.get("max_retries") or 0)
        for attempt in range(max_retries + 1):
            if attempt > 0:
                shutil.rmtree(manifest.trial_dir, ignore_errors=True)
                self._prime_trial_dir(manifest.trial_dir, manifest.config)
            exit_code = self._invoke_worker(manifest)
            result = self._read_json(manifest.trial_dir / "result.json")
            if result is None or exit_code != 0:
                _write_failure_result(
                    manifest.trial_dir,
                    manifest.config,
                    exception_type="WorkerProcessError",
                    exception_message=f"distributed worker exited with code {exit_code}",
                )
                result = self._read_json(manifest.trial_dir / "result.json")
            exc = result.get("exception_info") if isinstance(result, dict) else None
            exc_type = str(exc.get("exception_type") or "") if isinstance(exc, dict) else ""
            if not exc_type:
                return retries
            if attempt >= max_retries or not self._should_retry_exception(exc_type, retry):
                return retries
            retries += 1
            time.sleep(self._backoff_delay(attempt, retry))
        return retries

    @staticmethod
    def _prime_trial_dir(trial_dir: Path, config: dict[str, Any]) -> None:
        trial_dir.mkdir(parents=True, exist_ok=True)
        (trial_dir / "config.json").write_text(_json_dump(config), encoding="utf-8")

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any] | None:
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return None
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _should_retry_exception(exception_type: str, retry: dict[str, Any]) -> bool:
        excluded = set(retry.get("exclude_exceptions") or [])
        if exception_type in excluded:
            return False
        included = set(retry.get("include_exceptions") or [])
        if included and exception_type not in included:
            return False
        return True

    @staticmethod
    def _backoff_delay(attempt: int, retry: dict[str, Any]) -> float:
        wait_multiplier = float(retry.get("wait_multiplier") or 1.0)
        min_wait = float(retry.get("min_wait_sec") or 1.0)
        max_wait = float(retry.get("max_wait_sec") or 60.0)
        delay = min_wait * (wait_multiplier**attempt)
        return min(delay, max_wait)

    def _write_job_result(
        self,
        *,
        manifests: list[LocalDistributedTrialManifest],
        retries: int,
        finished: bool,
    ) -> None:
        completed = 0
        errored = 0
        cancelled = 0
        for manifest in manifests:
            result = self._read_json(manifest.trial_dir / "result.json")
            if not isinstance(result, dict):
                continue
            completed += 1
            exc = result.get("exception_info")
            if isinstance(exc, dict) and exc.get("exception_type"):
                errored += 1
                if exc.get("exception_type") == "CancelledError":
                    cancelled += 1
        running = 0 if finished else max(len(manifests) - completed, 0)
        payload = {
            "id": self.job_id,
            "started_at": self.started_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "updated_at": _utc_now_str(),
            "finished_at": _utc_now_str() if finished else None,
            "n_total_trials": len(manifests),
            "stats": {
                "n_completed_trials": completed,
                "n_errored_trials": errored,
                "n_running_trials": running,
                "n_pending_trials": max(len(manifests) - completed - running, 0),
                "n_cancelled_trials": cancelled,
                "n_retries": retries,
                "evals": {},
                "n_input_tokens": None,
                "n_cache_tokens": None,
                "n_output_tokens": None,
                "cost_usd": None,
            },
        }
        (self.job_dir / "result.json").write_text(_json_dump(payload), encoding="utf-8")

    def _write_state(
        self,
        manifests: list[LocalDistributedTrialManifest],
        *,
        status: str,
        retries: int,
    ) -> None:
        payload = {
            "status": status,
            "jobName": self.job_name,
            "generatedAt": _utc_now_str(),
            "trialNames": [manifest.trial_name for manifest in manifests],
            "retries": retries,
        }
        self.state_path.write_text(_json_dump(payload), encoding="utf-8")
