"""Chat session port — protocol between UserSim and the system under test."""

from __future__ import annotations

import inspect
from typing import Any, Dict, Protocol, Sequence

from playground.structured_exposure import build_structured_exposure
from playground.user_sim.tools import TurnAction


class ChatSessionPort(Protocol):
    """Drive a multi-turn chat with an application adapter or Harbor sidecar."""

    @property
    def session_id(self) -> str:
        """Active session id after the first turn, if the SUT assigns one."""

    def run_turn_sync(self, message: str) -> Dict[str, Any]:
        """Send one user message; return assistant turn view (assistantMessage, items, …)."""


def normalize_agent_turn(
    view: Dict[str, Any],
    user_message: str,
    *,
    structured_exposure_fields: Sequence[Any] | None = None,
) -> Dict[str, Any]:
    """Normalize heterogeneous SUT payloads into a common turn view."""
    turn = dict(view.get("turn") or view)
    assistant = str(
        turn.get("assistantMessage")
        or turn.get("assistantReply")
        or view.get("reply")
        or view.get("assistantMessage")
        or ""
    )
    merged = {**view, **turn}
    exposure = view.get("structuredExposure") or turn.get("structuredExposure")
    if not isinstance(exposure, list) or not exposure:
        exposure = build_structured_exposure(merged, structured_exposure_fields)
    return {
        "assistantMessage": assistant,
        "userMessage": user_message,
        "durationSeconds": turn.get("durationSeconds") or view.get("durationSeconds"),
        "structuredExposure": list(exposure),
    }


def run_session_action_sync(session: Any, action: TurnAction) -> Dict[str, Any]:
    """Execute a UserSim action on a sync session port."""
    if action.capability_tool:
        runner = getattr(session, "run_capability_sync", None)
        if callable(runner):
            result = runner(action.capability_tool, dict(action.capability_arguments or {}))
            if inspect.isawaitable(result):
                raise TypeError(
                    "session.run_capability_sync returned a coroutine; "
                    "use run_session_action_async in async runners"
                )
            return result
    message = (action.message or "").strip()
    result = session.run_turn_sync(message)
    if inspect.isawaitable(result):
        raise TypeError(
            "session.run_turn_sync returned a coroutine; use run_session_action_async"
        )
    return result


async def run_session_action_async(session: Any, action: TurnAction) -> Dict[str, Any]:
    """Execute a UserSim action on a sync or async session port."""
    if action.capability_tool:
        runner = getattr(session, "run_capability_sync", None)
        if callable(runner):
            result = runner(action.capability_tool, dict(action.capability_arguments or {}))
            if inspect.isawaitable(result):
                return await result
            return result
    message = (action.message or "").strip()
    result = session.run_turn_sync(message)
    if inspect.isawaitable(result):
        return await result
    return result
