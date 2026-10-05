"""Tool-driven user simulator chat eval runner."""

from __future__ import annotations

from itertools import count
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from playground.chatbot_task_config import (
    load_chatbot_task_config_for_task_path,
)
from playground.self_report_task_config import (
    load_self_report_schema_for_task_path,
)
from playground.task_content_bundle import (
    TaskContentBundle,
    load_task_content_bundle_for_task_path,
)
from playground.model_client import build_json_client
from playground.types import (
    MetricScores,
    Persona,
    PlaygroundConfig,
    PlaygroundResult,
    PlaygroundTurn,
)
from playground.user_sim.chatbot_labels import chatbot_display_name
from playground.user_sim.kickoff import get_goal_context
from playground.user_sim.port import (
    ChatSessionPort,
    normalize_agent_turn,
    run_session_action_async,
    run_session_action_sync,
)
from playground.user_sim.prompt import (
    assemble_report_system_prompt,
    prompt_bundle,
)
from playground.user_sim.self_report import final_self_report
from playground.user_sim.session import UserSimSession
from playground.user_sim.tool_client import build_tool_step_client


def _format_exposure_value(value: Any, *, kind: str) -> str:
    if kind == "item_list" and isinstance(value, list):
        parts = []
        for item in value:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("name") or "").strip()
            item_id = str(item.get("itemId") or item.get("id") or "").strip()
            if title and item_id:
                parts.append("{} ({})".format(title, item_id))
            elif title:
                parts.append(title)
            elif item_id:
                parts.append(item_id)
        return ", ".join(parts) or "[]"
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


# Used only when config.force_full_turns: if the sim tries to end early, this
# keeps it in-character and engaged so an adherence probe can keep applying
# pressure over the full conversation.
_CONTINUE_NUDGE = (
    "The conversation isn't over yet — the assistant follows up again. Stay in "
    "character and keep engaging naturally: react to what it just said, and hold "
    "to your own preferences and values as a real person would. Send one more "
    "message with the send_message tool (do not end the conversation)."
)


def _chatbot_observation(
    chatbot_label: str,
    assistant_message: str,
    structured_exposure: Optional[List[Dict[str, Any]]] = None,
) -> str:
    details = []
    for item in structured_exposure or []:
        value = _format_exposure_value(
            item.get("value"), kind=str(item.get("format") or "text")
        ).strip()
        if not value:
            continue
        label = str(item.get("label") or item.get("key") or "Visible detail")
        details.append("- {}: {}".format(label, value))
    extra = (
        "\nVisible structured details:\n{}\n".format("\n".join(details))
        if details
        else "\n"
    )
    return (
        '{label} Answer:\n"""{message}"""{extra}'
        "\nDecide your next move using the available tools."
    ).format(label=chatbot_label, message=assistant_message, extra=extra)


def _turn_indices(max_turns: int | None):
    return range(1, max_turns + 1) if max_turns is not None else count(1)


def _load_task_bundle(
    *,
    task_path: Optional[str],
    repo_root: Optional[Path],
) -> TaskContentBundle:
    if not task_path or repo_root is None:
        return TaskContentBundle()
    try:
        return load_task_content_bundle_for_task_path(task_path, repo_root=repo_root)
    except Exception:
        return TaskContentBundle()


def _load_chatbot_runtime_config(
    *,
    task_path: Optional[str],
    repo_root: Optional[Path],
):
    if not task_path or repo_root is None:
        return None
    try:
        return load_chatbot_task_config_for_task_path(task_path, repo_root=repo_root)
    except Exception:
        return None


def run_playground(
    session: ChatSessionPort,
    persona: Persona,
    sut_description: str,
    config: PlaygroundConfig,
    *,
    created_at: str,
    on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
    task_path: Optional[str] = None,
    persona_yaml_path: Optional[str] = None,
    repo_root: Optional[Path] = None,
) -> PlaygroundResult:
    def emit(event: Dict[str, Any]) -> None:
        if on_event is not None:
            on_event(event)

    goal_context = get_goal_context("scenario_default")
    chatbot_label = chatbot_display_name(config.application_id)
    task_bundle = _load_task_bundle(task_path=task_path, repo_root=repo_root)
    task_config = _load_chatbot_runtime_config(task_path=task_path, repo_root=repo_root)
    self_report_schema = load_self_report_schema_for_task_path(
        task_path or "",
        repo_root=repo_root or Path("."),
    )

    tool_client = build_tool_step_client(
        config.persona_model,
        capabilities=task_config.capabilities if task_config else None,
    )
    sim = UserSimSession(
        tool_client,
        persona,
        persona_yaml_path=persona_yaml_path,
        task_bundle=task_bundle,
    )
    prompts = prompt_bundle(
        persona,
        persona_yaml_path=persona_yaml_path,
        task_bundle=task_bundle,
        task_prompt=goal_context.description,
    )
    report_prompt = assemble_report_system_prompt(
        persona,
        persona_yaml_path=persona_yaml_path,
        task_bundle=task_bundle,
    )
    emit({"type": "prompts", "prompts": prompts})

    transcript: List[PlaygroundTurn] = []
    action = sim.opening_action()
    emit({"type": "phase", "phase": "persona_kickoff"})

    for index in _turn_indices(config.max_turns):
        message = (action.message or "").strip()
        if not message and not action.capability_tool:
            # Adherence probing keeps the pressure on: if the sim tried to end
            # early, nudge it to stay engaged until max_turns instead of stopping.
            if config.force_full_turns:
                action = sim.next_action(_CONTINUE_NUDGE)
                message = (action.message or "").strip()
            if not message and not action.capability_tool:
                break

        emit({"type": "user_message", "turnIndex": index, "message": message})
        emit({"type": "phase", "phase": "application_thinking", "userMessage": message})
        raw_view = run_session_action_sync(session, action)
        view = normalize_agent_turn(
            raw_view,
            message,
            structured_exposure_fields=task_config.structured_exposure if task_config else None,
        )
        assistant = str(view.get("assistantMessage") or "")
        structured_exposure = list(view.get("structuredExposure") or [])
        emit(
            {
                "type": "assistant_message",
                "turnIndex": index,
                "userMessage": message,
                "assistantMessage": assistant,
                "structuredExposure": structured_exposure,
                "durationSeconds": view.get("durationSeconds"),
            }
        )
        emit({"type": "phase", "phase": "persona_thinking"})
        action = sim.next_action(
            _chatbot_observation(chatbot_label, assistant, structured_exposure)
        )

        decision = action.decision if action.end_reason else "continue"
        turn = PlaygroundTurn(
            turn_index=index,
            user_message=message,
            assistant_message=assistant,
            structured_exposure=structured_exposure,
            decision=decision,
            duration_seconds=view.get("durationSeconds"),
        )
        transcript.append(turn)
        emit({"type": "turn", "turn": turn.to_dict()})

        if decision != "continue" and not config.force_full_turns:
            break

    emit({"type": "phase", "phase": "persona_feedback"})
    questionnaire = final_self_report(
        build_json_client(config.persona_model),
        system_prompt=report_prompt,
        persona=persona,
        transcript=transcript,
        schema=self_report_schema,
        chatbot_label=chatbot_label,
    )

    result = PlaygroundResult(
        config=config,
        persona=persona,
        sut_description=sut_description,
        transcript=transcript,
        questionnaire=questionnaire,
        metric_scores=MetricScores(num_turns=len(transcript)),
        created_at=created_at,
        prompts=prompts,
    )
    if on_event is not None:
        emit({"type": "done", "result": result.to_dict()})
    return result


async def run_playground_async(
    session: ChatSessionPort,
    persona: Persona,
    sut_description: str,
    config: PlaygroundConfig,
    *,
    created_at: str,
    on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
    task_path: Optional[str] = None,
    persona_yaml_path: Optional[str] = None,
    repo_root: Optional[Path] = None,
) -> PlaygroundResult:
    """Like :func:`run_playground` but awaits async Harbor sidecar turns."""

    def emit(event: Dict[str, Any]) -> None:
        if on_event is not None:
            on_event(event)

    goal_context = get_goal_context("scenario_default")
    chatbot_label = chatbot_display_name(config.application_id)
    task_bundle = _load_task_bundle(task_path=task_path, repo_root=repo_root)
    task_config = _load_chatbot_runtime_config(task_path=task_path, repo_root=repo_root)
    self_report_schema = load_self_report_schema_for_task_path(
        task_path or "",
        repo_root=repo_root or Path("."),
    )

    tool_client = build_tool_step_client(
        config.persona_model,
        capabilities=task_config.capabilities if task_config else None,
    )
    sim = UserSimSession(
        tool_client,
        persona,
        persona_yaml_path=persona_yaml_path,
        task_bundle=task_bundle,
    )
    prompts = prompt_bundle(
        persona,
        persona_yaml_path=persona_yaml_path,
        task_bundle=task_bundle,
        task_prompt=goal_context.description,
    )
    report_prompt = assemble_report_system_prompt(
        persona,
        persona_yaml_path=persona_yaml_path,
        task_bundle=task_bundle,
    )
    emit({"type": "prompts", "prompts": prompts})

    transcript: List[PlaygroundTurn] = []
    action = sim.opening_action()
    emit({"type": "phase", "phase": "persona_kickoff"})

    for index in _turn_indices(config.max_turns):
        message = (action.message or "").strip()
        if not message and not action.capability_tool:
            if config.force_full_turns:
                action = sim.next_action(_CONTINUE_NUDGE)
                message = (action.message or "").strip()
            if not message and not action.capability_tool:
                break

        emit({"type": "user_message", "turnIndex": index, "message": message})
        emit({"type": "phase", "phase": "application_thinking", "userMessage": message})
        raw_view = await run_session_action_async(session, action)
        view = normalize_agent_turn(
            raw_view,
            message,
            structured_exposure_fields=task_config.structured_exposure if task_config else None,
        )
        assistant = str(view.get("assistantMessage") or "")
        structured_exposure = list(view.get("structuredExposure") or [])
        emit(
            {
                "type": "assistant_message",
                "turnIndex": index,
                "userMessage": message,
                "assistantMessage": assistant,
                "structuredExposure": structured_exposure,
                "durationSeconds": view.get("durationSeconds"),
            }
        )
        emit({"type": "phase", "phase": "persona_thinking"})
        action = sim.next_action(
            _chatbot_observation(chatbot_label, assistant, structured_exposure)
        )

        decision = action.decision if action.end_reason else "continue"
        turn = PlaygroundTurn(
            turn_index=index,
            user_message=message,
            assistant_message=assistant,
            structured_exposure=structured_exposure,
            decision=decision,
            duration_seconds=view.get("durationSeconds"),
        )
        transcript.append(turn)
        emit({"type": "turn", "turn": turn.to_dict()})

        if decision != "continue" and not config.force_full_turns:
            break

    emit({"type": "phase", "phase": "persona_feedback"})
    questionnaire = final_self_report(
        build_json_client(config.persona_model),
        system_prompt=report_prompt,
        persona=persona,
        transcript=transcript,
        schema=self_report_schema,
        chatbot_label=chatbot_label,
    )

    result = PlaygroundResult(
        config=config,
        persona=persona,
        sut_description=sut_description,
        transcript=transcript,
        questionnaire=questionnaire,
        metric_scores=MetricScores(num_turns=len(transcript)),
        created_at=created_at,
        prompts=prompts,
    )
    if on_event is not None:
        emit({"type": "done", "result": result.to_dict()})
    return result
