"""Tool schemas and parsing for the user simulator."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from playground.chatbot_capabilities import ChatbotCapability, action_capabilities

_TOOL_SEND_PREFIX = re.compile(r"^(?:\s*Tool\s+send_message\s*:\s*)+", re.IGNORECASE)
_TOOL_END_PREFIX = re.compile(r"^\s*Tool\s+end_conversation\s*:\s*", re.IGNORECASE)
_XML_PARAMETER = re.compile(
    r"<parameter\s+name=[\"'][^\"']+[\"'][^>]*>.*?</parameter>",
    re.IGNORECASE | re.DOTALL,
)
_INVOKE_BLOCK = re.compile(r"<invoke\b[^>]*>.*?</invoke>", re.IGNORECASE | re.DOTALL)

END_REASONS = frozenset({"satisfied", "give_up", "out_of_scope", "transferred"})

_CORE_SEND_MESSAGE = {
    "type": "function",
    "function": {
        "name": "send_message",
        "description": "Send one natural-language message to the application chatbot.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The user message shown to the chatbot.",
                }
            },
            "required": ["message"],
            "additionalProperties": False,
        },
    },
}

_CORE_END_CONVERSATION = {
    "type": "function",
    "function": {
        "name": "end_conversation",
        "description": "End the chat when the goal is met or you would stop in real life.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "enum": sorted(END_REASONS),
                },
                "note": {
                    "type": "string",
                    "description": "Private one-line rationale (not sent to the chatbot).",
                },
            },
            "required": ["reason"],
            "additionalProperties": False,
        },
    },
}

_EXTRA_TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "upload_image": {
        "type": "function",
        "function": {
            "name": "upload_image",
            "description": (
                "Upload an image to the application chatbot (for example a medical "
                "photo) with an optional text note."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": (
                            "Path to a PNG/JPG image available in this eval environment."
                        ),
                    },
                    "text": {
                        "type": "string",
                        "description": "Optional text to send with the image.",
                    },
                },
                "required": ["image_path"],
                "additionalProperties": False,
            },
        },
    },
    "validate_output": {
        "type": "function",
        "function": {
            "name": "validate_output",
            "description": (
                "Confirm or reject a medical AI output when the product asks for "
                "human validation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "validation_result": {
                        "type": "string",
                        "enum": ["yes", "no"],
                        "description": "Whether you accept the model's output.",
                    },
                    "comments": {
                        "type": "string",
                        "description": "Optional short critique when rejecting.",
                    },
                },
                "required": ["validation_result"],
                "additionalProperties": False,
            },
        },
    },
}


@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TurnAction:
    """Parsed user-sim action for one driver step."""

    message: Optional[str] = None
    end_reason: Optional[str] = None
    note: str = ""
    capability_tool: Optional[str] = None
    capability_arguments: Dict[str, Any] = field(default_factory=dict)

    @property
    def decision(self) -> str:
        if self.end_reason == "satisfied":
            return "satisfied"
        if self.end_reason in {"give_up", "out_of_scope", "transferred"}:
            return "give_up"
        return "continue"


def tool_definitions(
    capabilities: Sequence[ChatbotCapability] | None = None,
) -> List[Dict[str, Any]]:
    """OpenAI-compatible tool definitions for this task's capabilities."""
    tools: List[Dict[str, Any]] = [_CORE_SEND_MESSAGE, _CORE_END_CONVERSATION]
    if capabilities is None:
        return tools
    seen = {"send_message", "end_conversation"}
    for capability in action_capabilities(capabilities):
        tool_name = capability.tool
        if not tool_name or tool_name in seen:
            continue
        schema = _EXTRA_TOOL_SCHEMAS.get(tool_name)
        if schema is None:
            continue
        tools.append(schema)
        seen.add(tool_name)
    return tools


def anthropic_tool_definitions(
    capabilities: Sequence[ChatbotCapability] | None = None,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for tool in tool_definitions(capabilities):
        fn = tool["function"]
        out.append(
            {
                "name": fn["name"],
                "description": fn.get("description", ""),
                "input_schema": fn["parameters"],
            }
        )
    return out


def normalize_sim_message(message: str) -> str:
    """Strip tool-syntax leaks models echo into ``send_message`` payloads."""
    text = str(message or "").strip()
    if not text:
        return ""
    while True:
        stripped = _TOOL_SEND_PREFIX.sub("", text, count=1).strip()
        if stripped == text:
            break
        text = stripped
    text = _TOOL_END_PREFIX.sub("", text).strip()
    text = _XML_PARAMETER.sub("", text).strip()
    text = _INVOKE_BLOCK.sub("", text).strip()
    return text


def _parse_arguments(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    return {}


def parse_tool_calls(calls: List[ToolCall]) -> TurnAction:
    action = TurnAction()
    for call in calls:
        args = call.arguments if isinstance(call.arguments, dict) else _parse_arguments(
            call.arguments
        )
        if call.name == "send_message":
            message = normalize_sim_message(str(args.get("message") or ""))
            if message:
                action.message = message
        elif call.name == "end_conversation":
            reason = str(args.get("reason") or "give_up").strip()
            if reason not in END_REASONS:
                reason = "give_up"
            action.end_reason = reason
            action.note = str(args.get("note") or action.note or "").strip()
        elif call.name in _EXTRA_TOOL_SCHEMAS:
            action.capability_tool = call.name
            action.capability_arguments = dict(args)
            if call.name == "upload_image":
                note = str(args.get("text") or "").strip()
                path = str(args.get("image_path") or "").strip()
                action.message = note or "[Uploaded image: {}]".format(path or "attachment")
            elif call.name == "validate_output":
                result = str(args.get("validation_result") or "").strip() or "yes"
                comments = str(args.get("comments") or "").strip()
                action.message = (
                    "[Validation: {}{}]".format(
                        result,
                        " — {}".format(comments) if comments else "",
                    )
                )
    if (
        not action.message
        and not action.end_reason
        and not action.capability_tool
        and len(calls) == 1
        and calls[0].name == "send_message"
    ):
        action.message = normalize_sim_message(
            str(calls[0].arguments.get("message") or "")
        )
    return action


def extract_stop_token(message: str) -> Optional[str]:
    text = (message or "").strip()
    if "###STOP###" in text:
        return "satisfied"
    return None
