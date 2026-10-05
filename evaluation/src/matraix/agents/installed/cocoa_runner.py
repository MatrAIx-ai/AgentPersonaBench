#!/usr/bin/env python3
"""Run a single CocoaAgent task inside an AIO Sandbox task container."""

from __future__ import annotations

import argparse
import base64
import binascii
import importlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

_COCOA_ROOT = os.environ.get("COCOA_ROOT", "/opt/cocoa-agent")
_PREPARED = False


def _prepare_cocoa() -> None:
    """Add cocoa-agent to sys.path and patch TaskExecutor for in-container sandbox."""
    global _PREPARED
    if _PREPARED:
        return
    _PREPARED = True

    if _COCOA_ROOT not in sys.path:
        sys.path.insert(0, _COCOA_ROOT)

    from executor import TaskExecutor

    _orig_setup = TaskExecutor.setup_environment
    _orig_cleanup = TaskExecutor.cleanup_environment

    def _patched_setup(self, task: dict, wait_time: int = 30) -> None:
        skip = self.config.get("sandbox", {}).get("skip_docker", False)
        if not skip:
            return _orig_setup(self, task, wait_time)

        import requests

        base = self.sandbox_client.base_url
        for _ in range(max(1, wait_time // 2)):
            try:
                response = requests.get(f"{base}/v1/ping", timeout=2)
                if response.status_code == 200:
                    if hasattr(self.sandbox_client, "_initialize_sdk_client"):
                        self.sandbox_client._initialize_sdk_client()
                    self.controller.clear_history()
                    if hasattr(self.controller, "reset_cost_tracking"):
                        self.controller.reset_cost_tracking()
                    return
            except Exception:
                pass
            time.sleep(2)
        raise RuntimeError(
            f"AIO Sandbox at {base} did not become ready within {wait_time}s"
        )

    def _patched_cleanup(self) -> None:
        skip = self.config.get("sandbox", {}).get("skip_docker", False)
        if skip:
            self.controller.clear_history()
        else:
            _orig_cleanup(self)

    TaskExecutor.setup_environment = _patched_setup
    TaskExecutor.cleanup_environment = _patched_cleanup

    _patch_agents_init()


def _patch_agents_init() -> None:
    """Avoid cocoa-agent eager imports that fail when optional deps are missing."""
    init_path = Path(_COCOA_ROOT) / "agents" / "__init__.py"
    safe_init = '''\
"""Agents package — minimal imports for Harbor runner."""
from .base import BaseAgent
from .cocoa_agent import CocoaAgent

__all__ = ["BaseAgent", "CocoaAgent"]
'''
    try:
        init_path.write_text(safe_init, encoding="utf-8")
    except OSError:
        pass

    if "agents" in sys.modules:
        del sys.modules["agents"]
    importlib.invalidate_caches()


def _controller_type(model: str) -> str:
    bare = model.split("/", 1)[-1].lower()
    if bare.startswith("claude"):
        return "claude"
    if bare.startswith("gemini"):
        return "gemini"
    if "qwen" in bare:
        return "qwen"
    if "deepseek" in bare:
        return "deepseek"
    return "llm"


def _api_key(model: str) -> str:
    if model.startswith("dashscope/"):
        value = os.environ.get("DASHSCOPE_API_KEY", "").strip()
        if value:
            return value
    for name in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "LLM_API_KEY", "DASHSCOPE_API_KEY"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    raise RuntimeError(
        "Set DASHSCOPE_API_KEY (for dashscope/*), or ANTHROPIC_API_KEY, OPENAI_API_KEY, "
        "or LLM_API_KEY for persona-cocoa"
    )


def _skip_docker() -> bool:
    raw = os.environ.get("COCOA_SKIP_DOCKER", "true").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _parse_tool_arguments(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw}
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    if raw is None:
        return {}
    return {"value": raw}


def _action_arguments(action: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in action.items()
        if key not in {"action_type", "tool_call_id"}
    }


def _split_assistant_content(content: str) -> tuple[str, str | None]:
    text = (content or "").strip()
    if not text:
        return "[agent step]", None
    if text.startswith("Thought:"):
        thought = text.removeprefix("Thought:").strip()
        return text, thought or None
    return text, None


def _assistant_message_content(message: dict[str, Any]) -> str:
    content = message.get("content")
    return content if isinstance(content, str) else ""


def _screenshot_map(result: dict[str, Any]) -> dict[str, str]:
    viz = result.get("visualization_data")
    if not isinstance(viz, dict):
        nested = result.get("trajectory")
        viz = nested.get("visualization_data") if isinstance(nested, dict) else {}
    if not isinstance(viz, dict):
        return {}

    mapping: dict[str, str] = {}
    for iteration in viz.get("iterations") or []:
        if not isinstance(iteration, dict):
            continue
        for action_item in iteration.get("actions") or []:
            if not isinstance(action_item, dict):
                continue
            action = action_item.get("action")
            if not isinstance(action, dict):
                continue
            tool_call_id = action.get("tool_call_id")
            screenshot = action_item.get("screenshot")
            if (
                isinstance(tool_call_id, str)
                and isinstance(screenshot, str)
                and screenshot
            ):
                mapping[tool_call_id] = screenshot
    return mapping


def _save_screenshot_b64(
    screenshot_data: str, images_dir: Path, step_number: int
) -> str | None:
    try:
        image_bytes = base64.b64decode(screenshot_data, validate=True)
    except (binascii.Error, ValueError):
        return None
    if not image_bytes:
        return None

    images_dir.mkdir(parents=True, exist_ok=True)
    dest = images_dir / f"step_{step_number:03d}.png"
    dest.write_bytes(image_bytes)
    return f"images/{dest.name}"


def _cocoa_conversation(result: dict[str, Any]) -> list[dict[str, Any]]:
    conversation = result.get("conversation")
    if isinstance(conversation, list):
        return [msg for msg in conversation if isinstance(msg, dict)]
    nested = result.get("trajectory")
    if isinstance(nested, dict) and isinstance(nested.get("conversation"), list):
        return [msg for msg in nested["conversation"] if isinstance(msg, dict)]
    return []


def _cocoa_execution_trace(result: dict[str, Any]) -> list[dict[str, Any]]:
    execution_trace = result.get("execution_trace")
    if isinstance(execution_trace, list):
        return [entry for entry in execution_trace if isinstance(entry, dict)]
    nested = result.get("trajectory")
    if isinstance(nested, dict) and isinstance(nested.get("execution_trace"), list):
        return [entry for entry in nested["execution_trace"] if isinstance(entry, dict)]
    return []


def _cocoa_summary(result: dict[str, Any]) -> dict[str, Any]:
    execution_trace = _cocoa_execution_trace(result)
    action_names: list[str] = []
    urls: list[str] = []
    for entry in execution_trace:
        action = entry.get("action")
        if not isinstance(action, dict):
            continue
        action_type = action.get("action_type")
        if isinstance(action_type, str):
            action_names.append(action_type)
        url = action.get("url")
        if isinstance(url, str) and url:
            urls.append(url)

    status = result.get("status")
    final_result = result.get("answer") or result.get("task_result")
    if not final_result and action_names and action_names[-1] == "task_complete":
        final_result = "Task completed"

    return {
        "final_result": final_result,
        "is_done": status in {"success", "failed", "error"},
        "is_successful": status == "success",
        "urls": urls,
        "action_names": action_names,
        "promoted_outputs": [],
        "status": status,
        "iterations": result.get("iterations"),
    }


def _flush_partial_trajectory(
    trajectory_path: Path,
    *,
    steps: list[dict[str, Any]],
    model_name: str,
    agent_version: str,
    session_id: str,
) -> None:
    """Best-effort checkpoint so the host can poll growing browser traces."""
    payload = {
        "schema_version": "ATIF-v1.6",
        "session_id": session_id,
        "agent": {
            "name": "cocoa",
            "version": agent_version,
            "model_name": model_name,
        },
        "steps": steps,
    }
    trajectory_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = trajectory_path.with_suffix(trajectory_path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(trajectory_path)


def _install_cocoa_live_flush(
    agent: Any,
    *,
    instruction: str,
    model_name: str,
    trajectory_path: Path,
    agent_version: str,
    session_id: str,
) -> None:
    """Hook Cocoa sandbox I/O so screenshots + ATIF land mid-run on the host mount."""
    executor = getattr(agent, "executor", None)
    if executor is None:
        return
    client = getattr(executor, "sandbox_client", None)
    controller = getattr(executor, "controller", None)
    if client is None or controller is None:
        return

    screenshots_by_call: dict[str, str] = {}
    synthetic_n = 0

    def _flush() -> None:
        try:
            partial = {
                "conversation": controller.get_history(),
                "execution_trace": client.get_history(),
                "visualization_data": {
                    "iterations": [
                        {
                            "actions": [
                                {
                                    "action": {"tool_call_id": call_id},
                                    "screenshot": shot,
                                }
                                for call_id, shot in screenshots_by_call.items()
                            ]
                        }
                    ]
                },
                "status": "running",
            }
            cocoa_to_atif(
                partial,
                instruction=instruction,
                model_name=model_name,
                trajectory_path=trajectory_path,
                agent_version=agent_version,
                session_id=session_id,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[cocoa] live trajectory flush failed: {exc}", flush=True)

    def _remember(call_id: str | None, screenshot_b64: str | None) -> None:
        nonlocal synthetic_n
        if not isinstance(screenshot_b64, str) or not screenshot_b64:
            _flush()
            return
        key = call_id if isinstance(call_id, str) and call_id else None
        if key is None:
            synthetic_n += 1
            key = f"live_shot_{synthetic_n}"
        screenshots_by_call[key] = screenshot_b64
        _flush()

    def _last_tool_call_id() -> str | None:
        try:
            hist = client.get_history()
        except Exception:
            return None
        if not isinstance(hist, list) or not hist:
            return None
        last = hist[-1]
        if not isinstance(last, dict):
            return None
        action = last.get("action")
        if isinstance(action, dict):
            call_id = action.get("tool_call_id")
            return call_id if isinstance(call_id, str) else None
        return None

    orig_take = getattr(client, "take_screenshot", None)
    if callable(orig_take):

        def take_screenshot(*args: Any, **kwargs: Any) -> Any:
            result = orig_take(*args, **kwargs)
            b64 = result[0] if isinstance(result, tuple) and result else None
            _remember(_last_tool_call_id(), b64 if isinstance(b64, str) else None)
            return result

        client.take_screenshot = take_screenshot

    orig_feedback = getattr(client, "get_feedback", None)
    if callable(orig_feedback):

        def get_feedback(action: Any, *args: Any, **kwargs: Any) -> Any:
            feedback = orig_feedback(action, *args, **kwargs)
            call_id = None
            action_type = None
            if isinstance(action, dict):
                raw_id = action.get("tool_call_id")
                call_id = raw_id if isinstance(raw_id, str) else None
                action_type = action.get("action_type")
            if (
                isinstance(feedback, dict)
                and action_type in {"browser_screenshot", "image_read"}
                and isinstance(feedback.get("image_base64"), str)
            ):
                _remember(call_id, feedback.get("image_base64"))
            else:
                # Conversation / execution_trace may have advanced without a new image.
                _flush()
            return feedback

        client.get_feedback = get_feedback

    orig_call = getattr(controller, "call", None)
    if callable(orig_call):

        def call(*args: Any, **kwargs: Any) -> Any:
            result = orig_call(*args, **kwargs)
            _flush()
            return result

        controller.call = call


def cocoa_to_atif(
    result: dict[str, Any],
    *,
    instruction: str,
    model_name: str,
    trajectory_path: Path,
    agent_version: str = "unknown",
    session_id: str | None = None,
) -> dict[str, Any]:
    """Convert a CocoaAgent result dict to ATIF-v1.6 for the Playground viewer."""
    conversation = _cocoa_conversation(result)
    execution_trace = _cocoa_execution_trace(result)
    screenshots = _screenshot_map(result)
    images_dir = trajectory_path.parent / "images"

    steps: list[dict[str, Any]] = [
        {
            "step_id": 1,
            "timestamp": None,
            "source": "user",
            "message": instruction,
        }
    ]
    session = session_id or str(uuid4())
    step_id = 2
    trace_idx = 0
    agent_step_number = 0

    for message in conversation:
        if message.get("role") != "assistant":
            continue

        agent_step_number += 1
        message_text, reasoning = _split_assistant_content(
            _assistant_message_content(message)
        )
        tool_calls_raw = message.get("tool_calls") or []

        tool_calls: list[dict[str, Any]] = []
        observation_results: list[dict[str, Any]] = []
        screenshot_rel: str | None = None

        for tc_idx, tool_call in enumerate(tool_calls_raw):
            if not isinstance(tool_call, dict):
                continue

            func = tool_call.get("function")
            if not isinstance(func, dict):
                func = {}

            trace_entry = (
                execution_trace[trace_idx] if trace_idx < len(execution_trace) else {}
            )
            trace_action = trace_entry.get("action")
            trace_action = trace_action if isinstance(trace_action, dict) else {}

            name = trace_action.get("action_type") or func.get("name") or "unknown"
            arguments = _action_arguments(trace_action)
            if not arguments:
                arguments = _parse_tool_arguments(func.get("arguments"))

            call_id = (
                tool_call.get("id")
                or trace_action.get("tool_call_id")
                or f"step{agent_step_number}_action{tc_idx + 1}"
            )
            tool_calls.append(
                {
                    "tool_call_id": call_id,
                    "function_name": name,
                    "arguments": arguments,
                }
            )

            feedback = trace_entry.get("feedback")
            feedback = feedback if isinstance(feedback, dict) else {}
            observation = feedback.get("message")
            if not isinstance(observation, str) or not observation.strip():
                observation = (
                    "Task completed"
                    if feedback.get("done")
                    else f"Action '{name}' executed"
                )
            observation_results.append(
                {
                    "source_call_id": call_id,
                    "content": observation,
                }
            )

            if screenshot_rel is None and isinstance(call_id, str):
                screenshot_data = screenshots.get(call_id)
                if screenshot_data:
                    screenshot_rel = _save_screenshot_b64(
                        screenshot_data, images_dir, agent_step_number
                    )

            trace_idx += 1

        if screenshot_rel:
            message_content: str | list[dict[str, Any]] = [
                {"type": "text", "text": message_text},
                {
                    "type": "image",
                    "source": {
                        "media_type": "image/png",
                        "path": screenshot_rel,
                    },
                },
            ]
        else:
            message_content = message_text

        agent_step: dict[str, Any] = {
            "step_id": step_id,
            "timestamp": None,
            "source": "agent",
            "model_name": model_name,
            "message": message_content,
        }
        if reasoning:
            agent_step["reasoning_content"] = reasoning
        if tool_calls:
            agent_step["tool_calls"] = tool_calls
        if observation_results:
            agent_step["observation"] = {"results": observation_results}
        steps.append(agent_step)
        step_id += 1
        _flush_partial_trajectory(
            trajectory_path,
            steps=steps,
            model_name=model_name,
            agent_version=agent_version,
            session_id=session,
        )

    cost = result.get("api_cost_stats")
    cost = cost if isinstance(cost, dict) else {}
    final_metrics = {
        "total_prompt_tokens": cost.get("total_input_tokens"),
        "total_completion_tokens": cost.get("total_output_tokens"),
        "total_cached_tokens": cost.get("total_cached_tokens"),
        "total_cost_usd": cost.get("total_cost_usd"),
        "total_steps": len(steps),
    }

    return {
        "schema_version": "ATIF-v1.6",
        "session_id": session,
        "agent": {
            "name": "cocoa",
            "version": agent_version,
            "model_name": model_name,
        },
        "steps": steps,
        "final_metrics": final_metrics,
        "extra": {"cocoa": _cocoa_summary(result)},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instruction", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--trajectory-path", required=True)
    args = parser.parse_args()

    _prepare_cocoa()

    port = int(os.environ.get("COCOA_SANDBOX_PORT", "8080"))
    base_url = os.environ.get("COCOA_SANDBOX_URL", f"http://localhost:{port}").rstrip(
        "/"
    )

    bare_model = args.model.split("/", 1)[-1]
    config = {
        "controller": {
            "type": _controller_type(args.model),
            "args": {
                "model": bare_model,
                "api_key": _api_key(args.model),
                "base_url": os.environ.get("LLM_BASE_URL")
                or os.environ.get("DASHSCOPE_API_BASE")
                or (
                    "https://dashscope.aliyuncs.com/compatible-mode/v1"
                    if args.model.startswith("dashscope/")
                    else ""
                ),
            },
        },
        "sandbox": {
            "client_type": "unified",
            "docker_port": port,
            "base_url": base_url,
            "max_iterations": int(os.environ.get("MAX_ITERATIONS", "30")),
            "skip_docker": _skip_docker(),
        },
    }

    from agents.cocoa_agent import CocoaAgent

    agent = CocoaAgent(config)
    task = {
        "instruction": args.instruction,
        "task_dir": "/app",
        "task_name": "harbor",
    }

    trajectory_path = Path(args.trajectory_path)
    trajectory_path.parent.mkdir(parents=True, exist_ok=True)
    agent_version = os.environ.get("COCOA_VERSION", "unknown")
    session_id = str(uuid4())

    result: dict
    try:
        agent.setup_environment(task)
        _install_cocoa_live_flush(
            agent,
            instruction=args.instruction,
            model_name=args.model,
            trajectory_path=trajectory_path,
            agent_version=agent_version,
            session_id=session_id,
        )
        result = agent.run_task(task)
    finally:
        try:
            agent.cleanup_environment()
        except Exception:
            pass

    trajectory = cocoa_to_atif(
        result,
        instruction=args.instruction,
        model_name=args.model,
        trajectory_path=trajectory_path,
        agent_version=agent_version,
        session_id=session_id,
    )
    tmp = trajectory_path.with_suffix(trajectory_path.suffix + ".tmp")
    tmp.write_text(json.dumps(trajectory, indent=2) + "\n", encoding="utf-8")
    tmp.replace(trajectory_path)

    if result.get("status") == "error":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
