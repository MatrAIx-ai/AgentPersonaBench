"""Tests for chatbot capability parsing and UserSim tool assembly."""

from __future__ import annotations

from playground.chatbot_capabilities import parse_capabilities
from playground.chatbot_task_config import _load_from_payload
from playground.user_sim.tools import parse_tool_calls, tool_definitions, ToolCall


def test_parse_capabilities_defaults_to_text_chat():
    caps = parse_capabilities(None)
    assert [c.id for c in caps] == ["text_chat"]


def test_parse_capabilities_adds_text_chat_when_missing():
    caps = parse_capabilities(["upload_image"])
    assert [c.id for c in caps] == ["text_chat", "upload_image"]
    assert caps[1].tool == "upload_image"


def test_tool_definitions_include_extra_action_tools():
    caps = parse_capabilities(["text_chat", "upload_image", "structured_exposure"])
    names = [tool["function"]["name"] for tool in tool_definitions(caps)]
    assert names == ["send_message", "end_conversation", "upload_image"]


def test_chatbot_yaml_structured_exposure_auto_adds_matching_capability():
    config = _load_from_payload(
        {
            "transport": "sidecar_http",
            "capabilities": ["text_chat"],
            "runtimeDefaults": {"applicationId": "meal_planning_nutrition"},
            "connection": {"baseUrl": "http://meal-plan-api:8000"},
            "protocol": {"sendMessage": {"path": "/v1/messages"}},
            "structuredExposure": {
                "fields": [
                    {
                        "key": "recommendedItems",
                        "label": "Recommended items",
                        "selector": "recommendedItems",
                        "format": "item_list",
                    }
                ]
            },
        }
    )
    assert [c.id for c in config.capabilities] == ["text_chat", "structured_exposure"]
    assert config.capabilities[1].kind == "exposure"
    assert config.structured_exposure[0].selector == "recommendedItems"


def test_parse_upload_tool_call():
    action = parse_tool_calls(
        [ToolCall("upload_image", {"image_path": "/tmp/a.png", "text": "rash"})]
    )
    assert action.capability_tool == "upload_image"
    assert action.capability_arguments["image_path"] == "/tmp/a.png"
    assert "rash" in (action.message or "")
