from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from fastapi import HTTPException
except ModuleNotFoundError:  # pragma: no cover - test env fallback
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str) -> None:
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

from playground.chatbot_task_config import (
    load_chatbot_task_config_for_task_path,
)
from playground.structured_exposure import build_structured_exposure
from playground.types import PlaygroundConfig


_SIDECAR_TASK_PATHS = {
    "finance_openbb": "application/tasks/chat_openbb-corporate-action-honesty",
    "meal_planning_nutrition": "application/tasks/chat_meal-planning-nutrition",
    "acme_support_api": "application/tasks/example-chat-api_support_chatbot",
}


class DirectApplicationSession:
    """Session wrapper for non-RecAI chatbot application adapters."""

    def __init__(self, config: PlaygroundConfig) -> None:
        self.config = config
        self.turns = []
        self._session_id: Optional[str] = None
        self._application = _application_for(config.application_id)
        self._task_config = _load_sidecar_task_config(config.application_id)

    def run_turn_sync(self, message: str) -> Dict[str, Any]:
        response = self._application.send_message(
            session_id=self._session_id,
            message=message,
            title="playground",
            context=config_context(self.config),
            engine=self.config.engine,
            bot_type="chat",
        )
        self._session_id = str(response["sessionId"])
        turn = dict(response.get("turn") or {})
        assistant = str(
            turn.get("assistantMessage")
            or turn.get("assistantReply")
            or response.get("reply")
            or ""
        )
        merged = {**response, **turn, "userMessage": message}
        exposure = build_structured_exposure(
            merged,
            self._task_config.structured_exposure if self._task_config else None,
        )
        view = {
            "assistantMessage": assistant,
            "userMessage": message,
            "structuredExposure": exposure,
        }
        self.turns.append(view)
        return view


def _load_sidecar_task_config(application_id: str):
    task_path = _SIDECAR_TASK_PATHS.get(application_id)
    if not task_path:
        return None
    repo_root = Path(__file__).resolve().parents[4]
    return load_chatbot_task_config_for_task_path(task_path, repo_root=repo_root)


def config_context(config: PlaygroundConfig) -> str:
    return config.application_context or config.domain


def _application_for(application_id: str) -> Any:
    if application_id == "finance_openbb":
        return HTTPChatbotApplication(
            application_id="finance_openbb",
            default_context="financial_research",
            base_url=_sidecar_base_url(
                "CHATBOT_UPSTREAM_FINANCE",
                "FINANCE_CHATBOT_URL",
                "http://127.0.0.1:8901",
            ),
        )
    if application_id == "meal_planning_nutrition":
        return HTTPChatbotApplication(
            application_id="meal_planning_nutrition",
            default_context="meal_planning",
            base_url=_sidecar_base_url(
                "CHATBOT_API_URL",
                "",
                "http://127.0.0.1:8905",
            ),
        )
    if application_id == "acme_support_api":
        return HTTPChatbotApplication(
            application_id="acme_support_api",
            default_context="customer_support",
            base_url=_sidecar_base_url(
                "CHATBOT_API_URL",
                "",
                "http://127.0.0.1:8904",
            ),
        )
    raise ValueError("unsupported direct application: {}".format(application_id))


def _sidecar_base_url(primary_env: str, legacy_env: str, default: str) -> str:
    return (
        os.environ.get(primary_env)
        or os.environ.get(legacy_env)
        or os.environ.get("CHATBOT_API_URL")
        or default
    )


class HTTPChatbotApplication:
    """HTTP client for task-owned chatbot application sidecars."""

    def __init__(self, *, application_id: str, default_context: str, base_url: str) -> None:
        self.application_id = application_id
        self.default_context = default_context
        self.base_url = base_url.rstrip("/")

    def send_message(
        self,
        *,
        session_id: Optional[str],
        message: str,
        title: Optional[str],
        context: str,
        engine: Optional[str],
        bot_type: Optional[str],
    ) -> Dict[str, Any]:
        body = {
            "sessionId": session_id,
            "message": message,
            "title": title,
            "applicationId": self.application_id,
            "applicationContext": context or self.default_context,
            "engine": engine,
            "botType": bot_type,
        }
        return self._request_json("POST", "/v1/messages", body=body)

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        body: Optional[Dict[str, Any]] = None,
        timeout: float = 180.0,
    ) -> Dict[str, Any]:
        url = "{}{}".format(self.base_url, path)
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(
                {key: value for key, value in body.items() if value is not None}
            ).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise HTTPException(status_code=exc.code, detail=detail) from exc
        except (TimeoutError, urllib.error.URLError) as exc:
            upstream_hint = {
                "finance_openbb": "CHATBOT_UPSTREAM_FINANCE",
                "meal_planning_nutrition": "CHATBOT_API_URL",
                "acme_support_api": "CHATBOT_API_URL",
            }.get(self.application_id, "CHATBOT_API_URL")
            raise HTTPException(
                status_code=503,
                detail=(
                    "{} sidecar unavailable at {}. Start the chatbot sidecar "
                    "or set {}."
                ).format(
                    self.application_id,
                    self.base_url,
                    upstream_hint,
                ),
            ) from exc
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=502,
                detail="{} sidecar returned invalid JSON".format(self.application_id),
            ) from exc
        if not isinstance(payload, dict):
            raise HTTPException(
                status_code=502,
                detail="{} sidecar returned non-object JSON".format(self.application_id),
            )
        return payload
