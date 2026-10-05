"""Harbor-backed web application evaluation helpers."""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

import yaml

from backend.service.config import harbor_persona_model
from playground.harbor.playground import (
    _default_harbor_command,
    _env_bool,
    _harbor_failure_summary,
    _read_env_file,
    _repo_root,
    _run_subprocess,
    harbor_persona_system_prompt,
    write_harbor_persona_yaml,
)
from playground.types import DEFAULT_PERSONA_MODEL, Persona
from matraix.persona_agent_context import apply_persona_context_to_agent_spec

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _default_harbor_web_runs_root() -> Path:
    return _repo_root() / "data" / "cache" / "playground" / "harbor_web_eval"


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("{} must contain a JSON object".format(path.name))
    return data


@dataclass(frozen=True)
class WebEvalTask:
    id: str
    title: str
    site_name: str
    site_url: str
    task_path: Path
    description: str
    output_artifact: str = "web_result.json"
    submission_profile: str = "web_result"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "siteName": self.site_name,
            "siteUrl": self.site_url,
            "description": self.description,
            "outputArtifact": self.output_artifact,
            "submissionProfile": self.submission_profile,
        }


@dataclass(frozen=True)
class HarborWebEvalConfig:
    persona_model: str = DEFAULT_PERSONA_MODEL
    mode: str = "harbor_persona_web"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "personaModel": self.persona_model,
            "mode": self.mode,
        }


@dataclass(frozen=True)
class WebEvalResultArtifact:
    selected_product_id: str
    selected_product_name: str
    need_satisfaction: int
    ease_of_use: int
    overall_experience_rating: int
    reason: str
    created_at: str
    valid: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any], *, created_at: str) -> "WebEvalResultArtifact":
        selected_product_id = str(
            data.get("selected_product_id", data.get("selectedProductId", ""))
        ).strip()
        selected_product_name = str(
            data.get("selected_product_name", data.get("selectedProductName", ""))
        ).strip()
        if not selected_product_id:
            raise ValueError("selected_product_id is required")
        if not selected_product_name:
            raise ValueError("selected_product_name is required")

        scores: Dict[str, int] = {}
        for snake, camel in (
            ("need_satisfaction", "needSatisfaction"),
            ("ease_of_use", "easeOfUse"),
            ("overall_experience_rating", "overallExperienceRating"),
        ):
            value = data.get(snake, data.get(camel))
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError("{} must be an integer from 1 to 10".format(snake))
            if value < 1 or value > 10:
                raise ValueError("{} must be between 1 and 10".format(snake))
            scores[snake] = value

        reason = str(data.get("reason", "")).strip()
        if len(reason) < 20:
            raise ValueError("reason must explain the website experience")

        return cls(
            selected_product_id=selected_product_id,
            selected_product_name=selected_product_name,
            need_satisfaction=scores["need_satisfaction"],
            ease_of_use=scores["ease_of_use"],
            overall_experience_rating=scores["overall_experience_rating"],
            reason=reason,
            created_at=created_at,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selectedProductId": self.selected_product_id,
            "selectedProductName": self.selected_product_name,
            "needSatisfaction": self.need_satisfaction,
            "easeOfUse": self.ease_of_use,
            "overallExperienceRating": self.overall_experience_rating,
            "reason": self.reason,
            "createdAt": self.created_at,
            "valid": self.valid,
        }


@dataclass(frozen=True)
class WebTrace:
    events: List[Dict[str, Any]]
    raw: Dict[str, Any]
    screenshots_dir: Optional[Path] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "events": [dict(event) for event in self.events],
            "raw": dict(self.raw),
        }


@dataclass(frozen=True)
class HarborWebEvalResult:
    config: HarborWebEvalConfig
    persona: Persona
    task: WebEvalTask
    web_result: WebEvalResultArtifact
    trace: WebTrace
    created_at: str
    prompts: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "persona": {
                "id": self.persona.id,
                "name": self.persona.name,
                "context": self.persona.context,
            },
            "task": self.task.to_dict(),
            "webResult": self.web_result.to_dict(),
            "trace": self.trace.to_dict(),
            "createdAt": self.created_at,
            "prompts": dict(self.prompts),
        }


def build_web_task_prompt(task: WebEvalTask) -> str:
    """Task-level instruction appended to the Harbor persona prompt."""
    return "\n".join(
        [
            "# Application task prompt: website user experience test",
            "",
            "Harbor supplies the persona system prompt. Use that persona as your",
            "identity, communication style, preferences, and decision-making style.",
            "",
            "You are testing a website application.",
            "",
            "Website: {}".format(task.site_name),
            "URL: {}".format(task.site_url),
            "",
            "Before using the site, state the concrete website task you will perform.",
            "Choose a realistic closed loop that fits your persona, such as finding,",
            "comparing, and selecting a product. Keep the task website-related and",
            "complete enough that you can judge whether the website supported it.",
            "",
            "Browse the website, compare at least two relevant options when possible,",
            "then evaluate the user experience from your persona's perspective.",
            "",
            "Finish with a final answer containing JSON. Playground will collect",
            "that final JSON as {}.".format(task.output_artifact),
            "",
            "```json",
            "{",
            '  "selected_product_id": "<product id shown on the site>",',
            '  "selected_product_name": "<product name shown on the site>",',
            '  "need_satisfaction": 1,',
            '  "ease_of_use": 1,',
            '  "overall_experience_rating": 1,',
            '  "reason": "<why this product and website experience fit or did not fit your needs>"',
            "}",
            "```",
            "",
            "Ratings must be integers from 1 to 10. Use only product ids and names",
            "shown on the site.",
            "",
        ]
    )


def _prompt_bundle(persona: Persona, task_prompt: str) -> Dict[str, str]:
    return {
        "harborPrompt": harbor_persona_system_prompt(persona),
        "taskPrompt": task_prompt,
    }


def _action_view(call: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": str(call.get("function_name", "")),
        "arguments": dict(call.get("arguments") or {}),
    }


def _screenshot_file_from_observation(step: Dict[str, Any]) -> Optional[str]:
    from backend.service.harbor_web_trace import screenshot_file_from_step

    return screenshot_file_from_step(step)


def _step_message_text(step: Dict[str, Any]) -> str:
    message = step.get("message", "")
    if isinstance(message, str):
        return message
    if isinstance(message, list):
        parts: List[str] = []
        for item in message:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        if parts:
            return "\n\n".join(parts)
    return str(message) if message else ""


def _trace_from_trajectory(trajectory: Dict[str, Any]) -> WebTrace:
    steps = trajectory.get("steps")
    events: List[Dict[str, Any]] = []
    if isinstance(steps, list):
        for index, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                continue
            calls = step.get("tool_calls") or []
            actions = [
                _action_view(call)
                for call in calls
                if isinstance(call, dict) and call.get("function_name")
            ]
            event = {
                "step": index,
                "source": str(step.get("source", "")),
                "message": _step_message_text(step),
                "actions": actions,
            }
            screenshot_file = _screenshot_file_from_observation(step)
            if screenshot_file:
                event["screenshotFile"] = screenshot_file
            events.append(event)
    return WebTrace(events=events, raw=trajectory)


def _read_trace(logs_dir: Optional[Path]) -> WebTrace:
    if logs_dir is None:
        return WebTrace(events=[], raw={})
    trajectory_path = logs_dir / "trajectory.json"
    if not trajectory_path.is_file():
        return WebTrace(events=[], raw={}, screenshots_dir=logs_dir)
    trace = _trace_from_trajectory(_read_json(trajectory_path))
    return WebTrace(events=trace.events, raw=trace.raw, screenshots_dir=logs_dir)


def _parse_json_object(raw: str) -> Optional[Dict[str, Any]]:
    text = raw.strip()
    if not text:
        return None
    fence = _JSON_FENCE_RE.search(text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        for index, char in enumerate(text):
            if char != "{":
                continue
            try:
                data, _ = decoder.raw_decode(text[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                return data
        return None
    return data if isinstance(data, dict) else None


def _valid_web_submission(data: Dict[str, Any]) -> bool:
    try:
        WebEvalResultArtifact.from_dict(data, created_at="1970-01-01T00:00:00Z")
    except ValueError:
        return False
    return True


def _payload_from_action(arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for field in ("message", "result", "text"):
        value = arguments.get(field)
        if isinstance(value, dict) and _valid_web_submission(value):
            return value
        if isinstance(value, str):
            parsed = _parse_json_object(value)
            if parsed is not None and _valid_web_submission(parsed):
                return parsed
    return None


def _extract_web_submission_from_trajectory(
    trajectory: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    steps = trajectory.get("steps")
    if not isinstance(steps, list):
        return None
    for step in reversed(steps):
        if not isinstance(step, dict) or step.get("source") != "agent":
            continue
        tool_calls = step.get("tool_calls") or []
        for call in reversed(tool_calls):
            if not isinstance(call, dict):
                continue
            arguments = call.get("arguments") or {}
            if isinstance(arguments, dict):
                payload = _payload_from_action(arguments)
                if payload is not None:
                    return payload
        message = step.get("message")
        if isinstance(message, str):
            parsed = _parse_json_object(message)
            if parsed is not None and _valid_web_submission(parsed):
                return parsed
    return None


def _extract_web_submission_from_logs(logs_dir: Optional[Path]) -> Optional[Dict[str, Any]]:
    if logs_dir is None:
        return None
    trajectory_path = logs_dir / "trajectory.json"
    if trajectory_path.is_file():
        try:
            payload = _extract_web_submission_from_trajectory(_read_json(trajectory_path))
        except ValueError:
            payload = None
        if payload is not None:
            return payload
    final_answer_path = logs_dir / "final_answer.txt"
    if final_answer_path.is_file():
        parsed = _parse_json_object(final_answer_path.read_text(encoding="utf-8"))
        if parsed is not None and _valid_web_submission(parsed):
            return parsed
    return None


def _materialize_missing_web_artifact(
    *,
    output_dir: Path,
    logs_dir: Optional[Path],
    task: WebEvalTask,
) -> bool:
    artifact_path = output_dir / task.output_artifact
    if artifact_path.is_file():
        return True
    payload = _extract_web_submission_from_logs(logs_dir)
    if payload is None:
        return False
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return True


def build_result_from_harbor_web_artifacts(
    *,
    output_dir: Path,
    logs_dir: Optional[Path],
    config: HarborWebEvalConfig,
    persona: Persona,
    task: WebEvalTask,
    created_at: str,
    prompts: Optional[Dict[str, str]] = None,
) -> HarborWebEvalResult:
    artifact_path = output_dir / task.output_artifact
    if not artifact_path.is_file():
        raise FileNotFoundError("missing web result artifact: {}".format(artifact_path))
    web_result = WebEvalResultArtifact.from_dict(
        _read_json(artifact_path),
        created_at=created_at,
    )
    trace = _read_trace(logs_dir)
    return HarborWebEvalResult(
        config=config,
        persona=persona,
        task=task,
        web_result=web_result,
        trace=trace,
        created_at=created_at,
        prompts=dict(prompts or {}),
    )


def _missing_required_output_artifacts(output_dir: Path, task: WebEvalTask) -> List[str]:
    return [task.output_artifact] if not (output_dir / task.output_artifact).is_file() else []


class HarborWebEvalRunner:
    """Callable runner that executes a Harbor persona-agent web job."""

    def __init__(
        self,
        *,
        repo_root: Optional[Path] = None,
        runs_root: Optional[Path] = None,
        command_runner: Callable[..., int] = _run_subprocess,
        harbor_command: Optional[Sequence[str]] = None,
    ) -> None:
        self.repo_root = Path(repo_root) if repo_root is not None else _repo_root()
        self.runs_root = (
            Path(runs_root) if runs_root is not None else _default_harbor_web_runs_root()
        )
        self.command_runner = command_runner
        self.harbor_command = tuple(harbor_command or _default_harbor_command())

    def __call__(
        self,
        persona: Persona,
        task: WebEvalTask,
        config: Optional[HarborWebEvalConfig] = None,
        *,
        created_at: str,
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> HarborWebEvalResult:
        config = config or HarborWebEvalConfig()

        def emit(event: Dict[str, Any]) -> None:
            if on_event is not None:
                on_event(event)

        job_name = "web-eval-{}".format(uuid.uuid4().hex[:12])
        run_dir = self.runs_root / job_name / "_inputs"
        run_dir.mkdir(parents=True, exist_ok=True)
        persona_path = write_harbor_persona_yaml(run_dir, persona)

        task_prompt = build_web_task_prompt(task)
        task_prompt_path = run_dir / "task_prompt.md"
        task_prompt_path.write_text(task_prompt, encoding="utf-8")
        prompts = _prompt_bundle(persona, task_prompt)

        task_path = task.task_path
        if not task_path.is_absolute():
            task_path = self.repo_root / task_path

        job_config_path = run_dir / "harbor_job.yaml"
        job_config = {
            "job_name": job_name,
            "jobs_dir": str(self.runs_root),
            "n_attempts": 1,
            "timeout_multiplier": 1.0,
            "n_concurrent_trials": 1,
            "quiet": False,
            "environment": {
                "type": "docker",
                "delete": _env_bool("MATRIX_HARBOR_DELETE", False),
                "force_build": _env_bool("MATRIX_HARBOR_FORCE_BUILD", False),
            },
            "agents": [
                apply_persona_context_to_agent_spec(
                    {
                        "name": "persona-computer-1",
                        "model_name": config.persona_model or harbor_persona_model(),
                        "kwargs": {
                            "persona_path": str(persona_path),
                        },
                    }
                )
            ],
            "tasks": [{"path": str(task_path)}],
            "extra_instruction_paths": [str(task_prompt_path)],
        }
        job_config_path.write_text(
            yaml.safe_dump(job_config, sort_keys=False),
            encoding="utf-8",
        )

        env = os.environ.copy()
        env_file = self.repo_root / ".env.local"
        for key, value in _read_env_file(env_file).items():
            env.setdefault(key, value)
        project_env = Path("/tmp/matraix-harbor-project-venv")
        if project_env.exists():
            env.setdefault("UV_PROJECT_ENVIRONMENT", str(project_env))
        command = [
            *self.harbor_command,
            "-c",
            str(job_config_path),
            "-y",
        ]
        if env_file.is_file():
            command.extend(["--env-file", str(env_file)])

        emit({"type": "prompts", "prompts": dict(prompts)})
        emit({"type": "phase", "phase": "harbor_starting"})
        code = self.command_runner(command, cwd=self.repo_root, env=env)
        if code != 0:
            raise RuntimeError("Harbor run failed with exit code {}".format(code))

        emit({"type": "phase", "phase": "harbor_collecting_artifacts"})
        output_dir = self._find_output_dir(job_name, task, require_artifact=False)
        logs_dir = self._find_logs_dir(job_name)
        _materialize_missing_web_artifact(
            output_dir=output_dir,
            logs_dir=logs_dir,
            task=task,
        )
        self._require_output_artifact(job_name, output_dir, task)
        result = build_result_from_harbor_web_artifacts(
            output_dir=output_dir,
            logs_dir=logs_dir,
            config=config,
            persona=persona,
            task=task,
            created_at=created_at,
            prompts=prompts,
        )
        emit({"type": "done", "result": result.to_dict()})
        return result

    def _find_output_dir(
        self,
        job_name: str,
        task: WebEvalTask,
        *,
        require_artifact: bool = True,
    ) -> Path:
        job_dir = self.runs_root / job_name
        matches = sorted(job_dir.glob("*/artifacts/app/output"))
        if not matches:
            matches = sorted(job_dir.rglob("artifacts/app/output"))
        if not matches:
            failure = _harbor_failure_summary(job_dir)
            if failure:
                raise RuntimeError(
                    "Harbor run did not produce output artifacts: {}".format(failure)
                )
            raise FileNotFoundError(
                "Harbor output artifacts not found under {}".format(job_dir)
            )
        output_dir = matches[0]
        if require_artifact:
            self._require_output_artifact(job_name, output_dir, task)
        return output_dir

    def _require_output_artifact(
        self,
        job_name: str,
        output_dir: Path,
        task: WebEvalTask,
    ) -> None:
        job_dir = self.runs_root / job_name
        missing = _missing_required_output_artifacts(output_dir, task)
        if missing:
            failure = _harbor_failure_summary(job_dir)
            detail = failure or "missing required artifacts: {}".format(
                ", ".join(missing)
            )
            raise RuntimeError(
                "Harbor web run did not produce required artifacts ({}): {}".format(
                    ", ".join(missing),
                    detail,
                )
            )

    def _find_logs_dir(self, job_name: str) -> Optional[Path]:
        job_dir = self.runs_root / job_name
        matches = sorted(job_dir.glob("*/agent"))
        if not matches:
            matches = sorted(job_dir.rglob("agent"))
        if not matches:
            matches = sorted(job_dir.glob("*/logs/agent"))
        if not matches:
            matches = sorted(job_dir.rglob("logs/agent"))
        return matches[0] if matches else None
