"""Helpers for parsing chat sidecar HTTP responses from host subprocess stdout."""

from __future__ import annotations

import json
from typing import Any


def parse_json_stdout(raw: str) -> dict[str, Any]:
    """Parse JSON from subprocess stdout, skipping shell profile noise before the payload."""
    text = (raw or "").strip()
    if not text:
        raise RuntimeError("chat sidecar returned empty response")
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    if start < 0:
        raise RuntimeError("chat sidecar returned invalid JSON: {}".format(text[:500]))
    try:
        parsed, _ = json.JSONDecoder().raw_decode(text, start)
    except json.JSONDecodeError as exc:
        raise RuntimeError("chat sidecar returned invalid JSON: {}".format(text[:500])) from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("chat sidecar response must be a JSON object")
    return parsed
