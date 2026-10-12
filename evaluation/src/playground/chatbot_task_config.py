"""Load task-owned chatbot runtime metadata from ``input/chatbot.yaml``."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

from playground.chatbot_capabilities import (
    ChatbotCapability,
    default_capabilities,
    parse_capabilities,
    with_structured_exposure_capability,
)
from playground.task_content_bundle import (
    content_dir_for_task_path,
    input_dir_for_task_path,
)


@dataclass(frozen=True)
class ChatbotConnectionConfig:
    base_url_env: str = ""
    legacy_base_url_env: str = ""
    base_url: str = ""
    health_path: str = "/health"

    def resolve_base_url(self, env: Mapping[str, str] | None = None) -> str:
        scope = env or os.environ
        candidates = []
        if self.base_url_env:
            candidates.append(str(scope.get(self.base_url_env, "")).strip())
        if self.legacy_base_url_env:
            candidates.append(str(scope.get(self.legacy_base_url_env, "")).strip())
        candidates.append(str(scope.get("MATRIX_CHATBOT_API_URL", "")).strip())
        candidates.append(self.base_url.strip())
        for candidate in candidates:
            if candidate:
                return candidate.rstrip("/")
        return ""


@dataclass(frozen=True)
class ChatbotProtocolConfig:
    method: str = "POST"
    path: str = "/v1/messages"
    session_id_field: str = "sessionId"
    message_field: str = "message"
    title_field: str = "title"
    bot_type_field: str = "botType"
    engine_field: str = ""
    domain_field: str = ""
    context_field: str = ""
    static_body: dict[str, Any] = field(default_factory=dict)
    response_session_id_field: str = "sessionId"
    response_reply_field: str = "reply"
    response_turn_field: str = "turn"


@dataclass(frozen=True)
class ChatbotStructuredExposureField:
    key: str
    label: str
    selector: str
    format: str = "text"


@dataclass(frozen=True)
class ChatbotRuntimeDefaults:
    application_id: str = ""
    application_context: str = ""
    domain: str = ""
    max_turns: int | None = None


@dataclass(frozen=True)
class ChatbotTaskConfig:
    transport: str = "http"
    runtime_defaults: ChatbotRuntimeDefaults = field(default_factory=ChatbotRuntimeDefaults)
    connection: ChatbotConnectionConfig = field(default_factory=ChatbotConnectionConfig)
    protocol: ChatbotProtocolConfig = field(default_factory=ChatbotProtocolConfig)
    capabilities: tuple[ChatbotCapability, ...] = field(default_factory=default_capabilities)
    structured_exposure: tuple[ChatbotStructuredExposureField, ...] = field(
        default_factory=tuple
    )
    artifacts: dict[str, str] = field(default_factory=dict)


def _as_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_sequence(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _as_string(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _read_chatbot_yaml(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("chatbot.yaml must be a mapping")
    return dict(payload)


def _as_optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _load_from_payload(payload: dict[str, Any]) -> ChatbotTaskConfig:
    runtime = _as_mapping(payload.get("runtimeDefaults"))
    connection = _as_mapping(payload.get("connection"))
    protocol = _as_mapping(payload.get("protocol"))
    structured_exposure = _as_mapping(payload.get("structuredExposure"))
    send = _as_mapping(protocol.get("sendMessage"))
    response = _as_mapping(protocol.get("response"))
    artifacts = {
        str(key): _as_string(value)
        for key, value in _as_mapping(payload.get("artifacts")).items()
        if _as_string(value)
    }
    exposure_fields = []
    for index, entry in enumerate(_as_sequence(structured_exposure.get("fields"))):
        field_payload = _as_mapping(entry)
        key = _as_string(field_payload.get("key"))
        selector = _as_string(field_payload.get("selector"))
        if not key or not selector:
            raise ValueError(
                "chatbot.yaml structuredExposure.fields[{}] requires key and selector".format(
                    index
                )
            )
        exposure_fields.append(
            ChatbotStructuredExposureField(
                key=key,
                label=_as_string(field_payload.get("label")) or key,
                selector=selector,
                format=_as_string(field_payload.get("format")) or "text",
            )
        )
    return ChatbotTaskConfig(
        transport=_as_string(payload.get("transport")) or "http",
        runtime_defaults=ChatbotRuntimeDefaults(
            application_id=_as_string(runtime.get("applicationId")),
            application_context=_as_string(runtime.get("applicationContext")),
            domain=_as_string(runtime.get("domain")),
            max_turns=max(1, parsed_max_turns)
            if (parsed_max_turns := _as_optional_int(runtime.get("maxTurns"))) is not None
            else None,
        ),
        connection=ChatbotConnectionConfig(
            base_url_env=_as_string(connection.get("baseUrlEnv")),
            legacy_base_url_env=_as_string(connection.get("legacyBaseUrlEnv")),
            base_url=_as_string(connection.get("baseUrl")),
            health_path=_as_string(connection.get("healthPath")) or "/health",
        ),
        protocol=ChatbotProtocolConfig(
            method=(_as_string(send.get("method")) or "POST").upper(),
            path=_as_string(send.get("path")) or "/v1/messages",
            session_id_field=_as_string(send.get("sessionIdField")) or "sessionId",
            message_field=_as_string(send.get("messageField")) or "message",
            title_field=_as_string(send.get("titleField")) or "title",
            bot_type_field=_as_string(send.get("botTypeField")) or "botType",
            engine_field=_as_string(send.get("engineField")),
            domain_field=_as_string(send.get("domainField")),
            context_field=_as_string(send.get("contextField")),
            static_body=_as_mapping(send.get("staticBody")),
            response_session_id_field=(
                _as_string(response.get("sessionIdField")) or "sessionId"
            ),
            response_reply_field=_as_string(response.get("replyField")) or "reply",
            response_turn_field=_as_string(response.get("turnField")) or "turn",
        ),
        capabilities=with_structured_exposure_capability(
            parse_capabilities(payload.get("capabilities")),
            has_exposure_fields=bool(exposure_fields),
        ),
        structured_exposure=tuple(exposure_fields),
        artifacts=artifacts,
    )


def load_chatbot_task_config_for_task_path(
    task_path: str,
    *,
    repo_root: Path,
) -> ChatbotTaskConfig | None:
    input_dir = input_dir_for_task_path(task_path, repo_root=repo_root)
    content_dir = content_dir_for_task_path(task_path, repo_root=repo_root)
    candidates: list[Path] = []
    if input_dir is not None:
        candidates.append(input_dir / "chatbot.yaml")
    if content_dir is not None:
        candidates.append(content_dir / "chatbot.yaml")
    for candidate in candidates:
        payload = _read_chatbot_yaml(candidate)
        if payload is not None:
            return _load_from_payload(payload)
    return None
