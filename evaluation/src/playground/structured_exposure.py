"""Build and normalize task-configured structured turn fields."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence


def lookup_path(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def build_structured_exposure(
    source: Dict[str, Any],
    fields: Sequence[Any] | None,
) -> List[Dict[str, Any]]:
    exposure: List[Dict[str, Any]] = []
    for field in fields or ():
        selector = str(getattr(field, "selector", "") or "")
        if not selector:
            continue
        value = lookup_path(source, selector)
        if value in (None, "", []):
            continue
        exposure.append(
            {
                "key": str(getattr(field, "key", "") or selector),
                "label": str(getattr(field, "label", "") or selector),
                "format": str(getattr(field, "format", "") or "text"),
                "value": value,
            }
        )
    return exposure


def item_list_from_exposure(exposure: Any) -> List[Dict[str, Any]]:
    if not isinstance(exposure, list):
        return []
    for field in exposure:
        if not isinstance(field, dict):
            continue
        if str(field.get("format") or "") != "item_list":
            continue
        value = field.get("value")
        if isinstance(value, list):
            return [dict(item) for item in value if isinstance(item, dict)]
    return []


def coerce_turn_view(view: Any) -> Dict[str, Any]:
    """Normalize a turn dict to the wire contract."""
    if not isinstance(view, dict):
        return {}
    out = dict(view)
    turn_id = out.get("turnId")
    if turn_id is not None and not isinstance(turn_id, str):
        out["turnId"] = str(turn_id)
    conv_id = out.get("conversationId")
    if conv_id is not None and not isinstance(conv_id, str):
        out["conversationId"] = str(conv_id)
    if not isinstance(out.get("plan"), list):
        out["plan"] = []
    exposure = out.get("structuredExposure")
    if not isinstance(exposure, list):
        exposure = []
    out["structuredExposure"] = [
        dict(item) for item in exposure if isinstance(item, dict)
    ]
    return out


def normalize_transcript_payload(
    transcript: Dict[str, Any],
    *,
    fields: Sequence[Any] | None = None,
) -> Dict[str, Any]:
    """Normalize transcript turns to the platform wire contract."""
    if not isinstance(transcript, dict):
        return {}
    out = dict(transcript)
    turns = out.get("turns")
    if not isinstance(turns, list):
        return out
    normalized: List[Dict[str, Any]] = []
    for index, turn in enumerate(turns):
        if not isinstance(turn, dict):
            continue
        coerced = coerce_turn_view(turn)
        if not coerced.get("structuredExposure"):
            exposure = build_structured_exposure({**out, **turn}, fields)
            coerced["structuredExposure"] = exposure
        if coerced.get("turnId") is None:
            coerced["turnId"] = str(turn.get("turnIndex", index))
        normalized.append(coerced)
    out["turns"] = normalized
    return out
