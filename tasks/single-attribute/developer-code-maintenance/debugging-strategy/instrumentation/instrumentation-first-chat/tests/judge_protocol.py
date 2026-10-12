"""Protocol 6.0: one completion report per incident; unchanged method verdict transport."""
from __future__ import annotations

import time
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import completion_protocol

REVISION = "6.0"
VERDICT_TOOL = {
    "name": "record_verdict",
    "description": "Record the one verdict for the criterion in the evaluator's request.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {"verdict": {"type": "string", "enum": ["HELD", "VIOLATED"]}},
        "required": ["verdict"],
        "additionalProperties": False,
    },
}


def parse_tool_verdict(content, stop_reason):
    if stop_reason != "tool_use" or not isinstance(content, list) or len(content) != 1:
        raise ValueError("judge must return exactly one complete verdict tool call")
    block = content[0]
    if not isinstance(block, dict) or block.get("type") != "tool_use":
        raise ValueError("judge returned non-tool content")
    if block.get("name") != "record_verdict" or not isinstance(block.get("id"), str) or not block["id"]:
        raise ValueError("judge returned an unknown or unidentified tool")
    obj = block.get("input")
    if not isinstance(obj, dict) or set(obj) != {"verdict"}:
        raise ValueError("judge verdict input must contain exactly verdict")
    if not isinstance(obj["verdict"], str) or obj["verdict"] not in ("HELD", "VIOLATED"):
        raise ValueError("judge verdict is outside the closed enum")
    return obj["verdict"]


def record_provider_error(item, exc, secrets=()):
    """Retain bounded API diagnostics, never request objects or headers."""
    def clean(value, limit):
        if not isinstance(value, str):
            return None
        for secret in secrets:
            if isinstance(secret, str) and secret:
                value = value.replace(secret, "[REDACTED]")
        value = re.sub(r"(?i)\b(?:sk-[A-Za-z0-9_-]+|bearer\s+\S+)", "[REDACTED]", value)
        return value[:limit]
    details = {"exception_type": type(exc).__name__}
    status = getattr(exc, "status_code", None)
    if type(status) is int and 100 <= status <= 599:
        details["status_code"] = status
    body = getattr(exc, "body", None)
    error = body.get("error", body) if isinstance(body, dict) else None
    if isinstance(error, dict):
        for key, limit in (("type", 100), ("message", 2000)):
            value = clean(error.get(key), limit)
            if value is not None:
                details[key] = value
    request_id = clean(getattr(exc, "request_id", None), 120)
    if request_id is not None:
        details["request_id"] = request_id
    item["provider_error"] = details


def call_judge(resolved, system, payload, item):
    import llm_client
    import usage
    is_completion = item.get("stage", "").startswith("completion/")
    if resolved.provider != "anthropic":
        from playground.openai_client import openai_model_is_reasoning_family
        reasoning = openai_model_is_reasoning_family(resolved.model)
        # Reasoning and visible output share the provider budget. Leave effort
        # selection to the unchanged shared client and its API default.
        max_tokens = 16000 if reasoning else (1800 if is_completion else 32)
        timeout = 180 if reasoning else 60
        item["max_tokens"] = max_tokens
        item["timeout_seconds"] = timeout
        item["protocol"] = "strict-completion-json-v6.0" if is_completion else "strict-text-v1"
        if is_completion:
            import json
            system += "\nReturn exactly one JSON object matching this schema: " + json.dumps(completion_protocol.COMPLETION_TOOL["input_schema"])
            item["system_prompt"] = system
        request = {"messages": [{"role": "system", "content": system},
                                {"role": "user", "content": payload}],
                   "model": resolved.model, "temperature": 0.0, "max_tokens": max_tokens,
                   "timeout": timeout, "retries": 1}
        item["request"] = {"transport": "llm_client.chat", **request}
        raw = llm_client.chat(**request)
        item["raw"] = raw
        return completion_protocol.strict_json(raw) if is_completion else raw
    import anthropic
    kwargs = {"api_key": llm_client.load_token("anthropic"), "timeout": 60, "max_retries": 0}
    if resolved.base_url:
        kwargs["base_url"] = resolved.base_url
    client = anthropic.Anthropic(**kwargs)
    # Task-local semantic completion criteria are versioned separately from the
    # unchanged method rule; submitted conversation is never evaluator instruction.
    system = system.replace(
        "Output exactly HELD or VIOLATED, without explanation, markup, or any other text.",
        "Use the record_verdict tool to return the requested HELD or VIOLATED value. Return no text.",
    )
    tool = completion_protocol.COMPLETION_TOOL if is_completion else VERDICT_TOOL
    system += ("\n\nTransport: call record_completion_evidence once, using the supplied closed schema. Return no text."
               if is_completion else "\n\nTransport: put the requested verdict in record_verdict.verdict; call that tool once.")
    item["protocol"] = "anthropic-completion-criteria-v6.0" if is_completion else "anthropic-forced-tool-v2"
    item["system_prompt"] = system
    item["request_tool"] = tool
    start = time.time()
    try:
        request = {"model": resolved.model, "max_tokens": 1800 if is_completion else 128,
                   "system": system, "messages": [{"role": "user", "content": payload}],
                   "tools": [tool],
                   "tool_choice": {"type": "tool", "name": tool["name"], "disable_parallel_tool_use": True}}
        item["request"] = {"transport": "anthropic.messages.create", **request}
        response = client.messages.create(**request)
    except Exception as exc:
        record_provider_error(item, exc, secrets=(kwargs["api_key"],))
        raise
    usage.record_response(resolved.model, response, started=start, source="chat-workflow-judge-tool")
    item["raw"] = [block.model_dump(mode="json") for block in response.content]
    item["stop_reason"] = response.stop_reason
    item["response_model"] = response.model
    item["response_id"] = response.id
    return (completion_protocol.parse_tool_response(item["raw"], response.stop_reason)
            if is_completion else parse_tool_verdict(item["raw"], response.stop_reason))
