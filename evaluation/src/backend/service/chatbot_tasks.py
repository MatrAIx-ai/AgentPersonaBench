"""Registry of Playground chatbot application tasks."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from backend.service.chatbot_sidecar_service import (
    resolve_health_url,
    sidecar_can_start,
    sidecar_reachable,
    sidecar_status,
)
from backend.service.example_task_catalog import (
    discover_application_tasks,
    repo_root,
    task_id_from_folder,
)
from backend.service.playground_task_registry_cache import get_cached_registry
from playground.chatbot_task_config import (
    ChatbotTaskConfig,
    load_chatbot_task_config_for_task_path,
)


@dataclass(frozen=True)
class ChatbotEvalTask:
    id: str
    title: str
    description: str
    task_path: Union[str, Path]
    transport: str = "http"
    application_id: str = ""
    application_context: str = ""
    default_domain: str = ""
    meta_type: str = "chatbot"
    domain: str = ""
    difficulty: str = "easy"
    task_kind: str = "task"
    tags: tuple[str, ...] = ()
    available: Optional[bool] = None
    can_start: bool = False
    health_url: str = ""
    status_detail: str = ""
    capabilities: tuple[dict[str, Any], ...] = ()

    def _normalized_task_path(self) -> str:
        task_path = self.task_path
        if isinstance(task_path, Path):
            parts = task_path.parts
            if "application" in parts and "tasks" in parts:
                idx = parts.index("tasks")
                return "/".join(parts[idx - 1 :])
            return str(task_path)
        return str(task_path)

    def to_summary_dict(self) -> Dict[str, Any]:
        """List-endpoint payload without live sidecar health probes."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "taskPath": self._normalized_task_path(),
            "transport": self.transport,
            "applicationId": self.application_id,
            "applicationContext": self.application_context,
            "defaultDomain": self.default_domain,
            "metaType": self.meta_type,
            "domain": self.domain,
            "difficulty": self.difficulty,
            "taskKind": self.task_kind,
            "tags": list(self.tags),
            "capabilities": list(self.capabilities),
            "canStart": self.can_start,
            "healthUrl": self.health_url,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            **self.to_summary_dict(),
            "available": self.available,
            "statusDetail": self.status_detail,
        }


def _static_sidecar_fields(task_config: ChatbotTaskConfig | None) -> dict[str, Any]:
    """Sidecar metadata from config without network probes."""
    if task_config is None:
        return {"can_start": False, "health_url": ""}
    application_id = task_config.runtime_defaults.application_id
    try:
        health_url = resolve_health_url(application_id)
        return {
            "can_start": sidecar_can_start(application_id),
            "health_url": health_url,
        }
    except ValueError:
        base_url = task_config.connection.resolve_base_url()
        return {"can_start": False, "health_url": base_url or ""}


def _task_availability(task_config: ChatbotTaskConfig) -> dict[str, Any]:
    application_id = task_config.runtime_defaults.application_id
    try:
        status = sidecar_status(application_id, repo_root=repo_root())
    except ValueError:
        base_url = task_config.connection.resolve_base_url()
        if base_url:
            ok = sidecar_reachable(base_url)
            return {
                "available": ok,
                "canStart": False,
                "healthUrl": base_url,
                "statusDetail": (
                    "Chat API ready at {}.".format(base_url)
                    if ok
                    else "Chat API not ready at {}.".format(base_url)
                ),
            }
        if task_config.transport == "mcp":
            return {
                "available": None,
                "canStart": False,
                "healthUrl": "",
                "statusDetail": "MCP-backed task; no HTTP readiness check is configured.",
            }
        return {
            "available": None,
            "canStart": False,
            "healthUrl": "",
            "statusDetail": "No HTTP readiness check is configured for this chatbot task.",
        }
    return {
        "available": status["ok"],
        "canStart": status["canStart"],
        "healthUrl": status["healthUrl"],
        "statusDetail": status["detail"],
    }


def _build_registry() -> Dict[str, ChatbotEvalTask]:
    tasks: Dict[str, ChatbotEvalTask] = {}
    root = repo_root()
    for record in discover_application_tasks(application_type="chatbot"):
        task_id = task_id_from_folder(record.folder_name)
        task_config = load_chatbot_task_config_for_task_path(record.task_path, repo_root=root)
        static_sidecar = _static_sidecar_fields(task_config)
        runtime = task_config.runtime_defaults if task_config is not None else None
        capabilities = (
            tuple(item.to_public_dict() for item in task_config.capabilities)
            if task_config is not None
            else ()
        )
        tasks[task_id] = ChatbotEvalTask(
            id=task_id,
            title=record.title,
            description=record.description,
            task_path=record.task_path,
            transport=task_config.transport if task_config is not None else "http",
            application_id=runtime.application_id if runtime is not None else "",
            application_context=runtime.application_context if runtime is not None else "",
            default_domain=runtime.domain if runtime is not None else "",
            meta_type=record.meta_type,
            domain=record.domain,
            difficulty=record.difficulty,
            task_kind=record.task_kind,
            tags=tuple(record.tags),
            available=None,
            can_start=bool(static_sidecar["can_start"]),
            health_url=str(static_sidecar["health_url"] or ""),
            status_detail="",
            capabilities=capabilities,
        )
    return tasks


def _registry() -> Dict[str, ChatbotEvalTask]:
    return get_cached_registry("chatbot", _build_registry)


def list_chatbot_eval_tasks() -> List[ChatbotEvalTask]:
    return list(_registry().values())


def get_chatbot_eval_task(task_id: str) -> ChatbotEvalTask:
    try:
        task = _registry()[task_id]
    except KeyError as exc:
        raise KeyError("unknown chatbot eval task: {}".format(task_id)) from exc
    root = repo_root()
    task_config = load_chatbot_task_config_for_task_path(task.task_path, repo_root=root)
    if task_config is None:
        return task
    availability = _task_availability(task_config)

    return replace(
        task,
        available=availability.get("available"),
        can_start=bool(availability.get("canStart", task.can_start)),
        health_url=str(availability.get("healthUrl") or task.health_url or ""),
        status_detail=str(availability.get("statusDetail") or ""),
    )
