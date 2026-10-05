"""Build the ``TurnView`` the UI renders from a raw ``RecBotTurnResult`` dict.

The backend returns a :class:`recbot.types.RecBotTurnResult` whose ``.to_dict()``
shape is (approximately)::

    {
      "backend": "interecagent",
      "conversation_id": "...",
      "turn_id": "...",
      "user_message": {"role": "user", "content": "..."},
      "assistant_message": {"role": "assistant", "content": "..."},
      "native_action": {"raw": <str|dict|list>, "raw_tool_plan": [...]},
      "trace": {
        "raw_tool_plan": [...],
        "raw_tool_outputs": <any>,
        "recommended_item_ids": ["cmu:54166", ...]
      }
    }

:class:`TraceView` turns that into a flat, UI-friendly ``TurnView`` dict:

    {
      "turnId": "...",
      "userMessage": "...",
      "assistantMessage": "...",
      "plan": [{"tool": "HardFilter", "detail": "...", "status": "ok"}, ...],
      "structuredExposure": [
          {"key": "...", "label": "...", "format": "item_list", "value": [...]},
      ],
      "nativeRaw": <stringified native_action.raw>,
      "rawToolOutputs": <trace.raw_tool_outputs as-is>,
    }

Parsing the tool plan is **best-effort**: InteRecAgent emits plans in a few
shapes (a structured list of steps, or a free-form "thought/plan" string that
mentions tools like BufferStore / HardFilter / Rank / Map). We extract what we
can and never raise on a shape we do not recognize.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from playground.structured_exposure import (
    coerce_turn_view,
    item_list_from_exposure,
)

__all__ = ["TraceView", "normalize_turn_view", "item_list_from_exposure"]


def normalize_turn_view(view: Any) -> Dict[str, Any]:
    """Coerce a (possibly legacy-shaped) persisted ``TurnView`` dict to contract."""
    return coerce_turn_view(view)

# Canonical InteRecAgent tool names we know how to render. Matching is
# case-insensitive and tolerant of suffixes like "Tool".
_KNOWN_TOOLS = ["BufferStore", "HardFilter", "SoftFilter", "Rank", "Map"]

_TOOL_LOOKUP = {t.lower(): t for t in _KNOWN_TOOLS}


class TraceView:
    """Namespace for the :meth:`build` factory (no instance state)."""

    @staticmethod
    def from_result(
        result: Any,
        catalog: Any,
        duration_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Build a ``TurnView`` from a ``RecBotTurnResult`` (or its dict form).

        This is the contract entry point. ``result`` may be a
        :class:`recbot.types.RecBotTurnResult` (anything with ``to_dict()``) or
        an already-dict payload; it is normalized to a dict and handed to
        :meth:`build`.

        Parameters
        ----------
        result:
            A ``RecBotTurnResult`` instance or an equivalent dict.
        catalog:
            A :class:`~backend.service.catalog_index.CatalogIndex` (or anything
            exposing ``get(item_id)``), used to resolve recommended ids.
        duration_seconds:
            Optional wall-clock duration of the turn, surfaced as
            ``durationSeconds`` for the UI.
        """
        if hasattr(result, "to_dict"):
            result_dict = result.to_dict()
        elif isinstance(result, dict):
            result_dict = result
        else:
            result_dict = {}
        return TraceView.build(result_dict, catalog, duration_seconds=duration_seconds)

    @staticmethod
    def build(
        result_dict: Dict[str, Any],
        catalog: Any,
        duration_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Construct a ``TurnView`` dict from a ``RecBotTurnResult`` dict.

        Parameters
        ----------
        result_dict:
            The output of ``RecBotTurnResult.to_dict()`` (or an equivalent
            dict). Missing / malformed fields are tolerated.
        catalog:
            A :class:`~backend.service.catalog_index.CatalogIndex` (or anything
            exposing ``get(item_id)`` / ``title_for(item_id)``). Used to resolve
            recommended ids to titles and metadata.
        duration_seconds:
            Optional wall-clock duration of the turn, surfaced as
            ``durationSeconds``.
        """
        result_dict = result_dict or {}

        native_action = _as_dict(result_dict.get("native_action"))
        trace = _as_dict(result_dict.get("trace"))

        user_message = _message_text(result_dict.get("user_message"))
        assistant_message = _message_text(result_dict.get("assistant_message"))

        native_raw_value = native_action.get("raw")
        native_raw = _stringify_raw(native_raw_value)

        # Tool plan: prefer an explicit structured plan, fall back to parsing
        # the native raw text.
        raw_plan = trace.get("raw_tool_plan")
        if not raw_plan:
            raw_plan = native_action.get("raw_tool_plan")
        plan = TraceView._build_plan(raw_plan, native_raw_value)

        recommended_ids = _string_list(trace.get("recommended_item_ids"))
        resolved_items = TraceView._resolve_items(
            recommended_ids, trace, catalog
        )
        structured_exposure: List[Dict[str, Any]] = []
        if resolved_items:
            structured_exposure.append(
                {
                    "key": "structuredItems",
                    "label": "Structured details",
                    "format": "item_list",
                    "value": resolved_items,
                }
            )

        # The real recbot backend produces an int turn_id, but the wire/UI
        # contract treats turnId as a string; coerce so API response validation
        # passes regardless of which backend produced the result.
        turn_id_value = result_dict.get("turn_id")
        return {
            "turnId": str(turn_id_value) if turn_id_value is not None else None,
            "conversationId": result_dict.get("conversation_id"),
            "backend": result_dict.get("backend"),
            "userMessage": user_message,
            "assistantMessage": assistant_message,
            "plan": plan,
            "structuredExposure": structured_exposure,
            "nativeRaw": native_raw,
            "rawToolOutputs": trace.get("raw_tool_outputs"),
            "durationSeconds": (
                float(duration_seconds) if duration_seconds is not None else None
            ),
        }

    # ------------------------------------------------------------------ #
    # Tool plan parsing
    # ------------------------------------------------------------------ #
    @staticmethod
    def _build_plan(
        raw_plan: Any, native_raw_value: Any
    ) -> List[Dict[str, Optional[str]]]:
        """Return a list of ``{tool, detail, status}`` steps (best-effort)."""
        steps = TraceView._plan_from_structured(raw_plan)
        if steps:
            return steps
        steps = TraceView._plan_from_text(native_raw_value)
        return steps

    @staticmethod
    def _plan_from_structured(raw_plan: Any) -> List[Dict[str, Optional[str]]]:
        """Parse a structured plan (list of dict/str/list steps)."""
        if not isinstance(raw_plan, list):
            return []
        steps: List[Dict[str, Optional[str]]] = []
        for entry in raw_plan:
            step = TraceView._step_from_entry(entry)
            if step is not None:
                steps.append(step)
        return steps

    @staticmethod
    def _step_from_entry(entry: Any) -> Optional[Dict[str, Optional[str]]]:
        if isinstance(entry, dict):
            tool = _first_str(
                entry, ["tool", "tool_name", "name", "action", "op"]
            )
            detail = _first_str(
                entry,
                [
                    "detail",
                    "input",
                    "tool_input",
                    "args",
                    "arguments",
                    "description",
                    "thought",
                    "observation",
                ],
            )
            if detail is None:
                # Fall back to compactly serializing any non-tool fields.
                rest = {
                    k: v
                    for k, v in entry.items()
                    if k not in {"tool", "tool_name", "name", "action", "op", "status"}
                }
                detail = _compact_json(rest) if rest else None
            status = _first_str(entry, ["status"]) or "ok"
            tool_name = _canonical_tool(tool) if tool else None
            if tool_name is None and detail is None:
                return None
            return {
                "tool": tool_name or (tool or "step"),
                "detail": detail,
                "status": status,
            }
        if isinstance(entry, (list, tuple)) and entry:
            tool = entry[0] if isinstance(entry[0], str) else None
            detail_parts = [str(x) for x in entry[1:]]
            detail = ", ".join(detail_parts) if detail_parts else None
            tool_name = _canonical_tool(tool) if tool else None
            return {
                "tool": tool_name or (tool or "step"),
                "detail": detail,
                "status": "ok",
            }
        if isinstance(entry, str) and entry.strip():
            tool_name = _detect_tool(entry)
            return {
                "tool": tool_name or "step",
                "detail": entry.strip(),
                "status": "ok",
            }
        return None

    @staticmethod
    def _plan_from_text(native_raw_value: Any) -> List[Dict[str, Optional[str]]]:
        """Heuristically extract a plan from free-form native text.

        Looks for lines / fragments mentioning the known tools and packages
        each as a step. This is a fallback for backends that only emit a
        thought/plan blob rather than structured steps.
        """
        text = _coerce_text(native_raw_value)
        if not text:
            return []
        steps: List[Dict[str, Optional[str]]] = []
        seen_positions: List[int] = []
        # Find tool mentions in order of appearance.
        pattern = re.compile(
            r"\b(" + "|".join(re.escape(t) for t in _KNOWN_TOOLS) + r")\b",
            re.IGNORECASE,
        )
        matches = list(pattern.finditer(text))
        for i, m in enumerate(matches):
            tool = _canonical_tool(m.group(1))
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            detail = text[start:end].strip(" \t\r\n:->,.;")
            detail = re.sub(r"\s+", " ", detail)
            if len(detail) > 200:
                detail = detail[:197] + "..."
            steps.append(
                {
                    "tool": tool or m.group(1),
                    "detail": detail or None,
                    "status": "ok",
                }
            )
            seen_positions.append(m.start())
        return steps

    # ------------------------------------------------------------------ #
    # Recommended item resolution
    # ------------------------------------------------------------------ #
    @staticmethod
    def _resolve_items(
        recommended_ids: List[str], trace: Dict[str, Any], catalog: Any
    ) -> List[Dict[str, Any]]:
        scores = _score_map(trace)
        trace_titles = _trace_title_map(trace)
        items: List[Dict[str, Any]] = []
        for rank, item_id in enumerate(recommended_ids):
            entry: Dict[str, Any] = {
                "itemId": item_id,
                "rank": rank + 1,
                "title": None,
                "meta": None,
                "score": scores.get(item_id),
            }
            # The agent's own trace title is authoritative: it comes from the
            # exact item corpus the agent ranked over (the run's domain). The
            # catalog is supplementary — and may be a *different* domain, where
            # the same integer id resolves to an unrelated item. So prefer the
            # trace title; only borrow the catalog's title/meta when the catalog
            # has no competing trace title OR resolves to the very same item.
            trace_title = trace_titles.get(item_id)
            if isinstance(trace_title, str) and trace_title:
                entry["title"] = trace_title

            item = catalog.get(item_id) if catalog is not None else None
            if item:
                catalog_title = item.get("title")
                catalog_title = catalog_title if isinstance(catalog_title, str) else None
                if not entry["title"]:
                    entry["title"] = catalog_title
                # Trust catalog meta only when it describes the SAME item the
                # agent named (guards against a cross-domain id collision).
                if catalog_title and (not trace_title or catalog_title == trace_title):
                    entry["meta"] = _meta_line(item)
            items.append(entry)
        return items


# ---------------------------------------------------------------------- #
# Module-level helpers
# ---------------------------------------------------------------------- #
def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _message_text(value: Any) -> Optional[str]:
    """Extract message content from a ChatMessage dict or a bare string."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        content = value.get("content")
        if isinstance(content, str):
            return content
    return None


def _string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [v for v in value if isinstance(v, str) and v]


def _first_str(d: Dict[str, Any], keys: List[str]) -> Optional[str]:
    for key in keys:
        if key in d:
            v = d[key]
            if isinstance(v, str) and v.strip():
                return v.strip()
            if isinstance(v, (int, float, bool)):
                return str(v)
            if isinstance(v, (dict, list)):
                return _compact_json(v)
    return None


def _canonical_tool(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    key = name.strip().lower()
    # Tolerate trailing "tool" suffix, e.g. "RankingTool" / "MapTool".
    if key in _TOOL_LOOKUP:
        return _TOOL_LOOKUP[key]
    for base in _KNOWN_TOOLS:
        if key.startswith(base.lower()):
            return base
    return None


def _detect_tool(text: str) -> Optional[str]:
    lowered = text.lower()
    for base in _KNOWN_TOOLS:
        if base.lower() in lowered:
            return base
    return None


def _compact_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        return str(value)


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(value)
    return str(value)


def _stringify_raw(value: Any) -> str:
    """Pretty stringify ``native_action.raw`` for display in the inspector."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=False, indent=2)
        except (TypeError, ValueError):
            return str(value)
    return str(value)


def _meta_line(item: Dict[str, Any]) -> Optional[str]:
    """Build a compact "1941 · Film-noir, Mystery" style meta string."""
    parts: List[str] = []
    metadata = item.get("metadata")
    if isinstance(metadata, dict):
        year = metadata.get("release_year")
        if isinstance(year, (int, str)) and str(year).strip():
            parts.append(str(year))
    cats = item.get("categories")
    if isinstance(cats, list):
        cat_strs = [c for c in cats if isinstance(c, str)][:3]
        if cat_strs:
            parts.append(", ".join(cat_strs))
    if not parts:
        return None
    return " · ".join(parts)


def _trace_title_map(trace: Dict[str, Any]) -> Dict[str, str]:
    """Map ``{str(id): title}`` from ``trace["recommended_items"]``.

    The bridge populates ``recommended_items`` as ``[{"id", "title"}, ...]``
    (titles resolved from the agent's own item corpus), which is the only
    reliable title source for ``recai_resources`` integer ids that the
    external-keyed :class:`CatalogIndex` cannot resolve.
    """
    out: Dict[str, str] = {}
    raw = trace.get("recommended_items")
    if not isinstance(raw, list):
        return out
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        item_id = entry.get("id")
        title = entry.get("title")
        if item_id is not None and isinstance(title, str) and title:
            out[str(item_id)] = title
    return out


def _score_map(trace: Dict[str, Any]) -> Dict[str, float]:
    """Best-effort extraction of per-item scores from the trace.

    Recognizes a few shapes the backend might emit:

    * ``trace["recommended_item_scores"]`` as ``{id: score}`` or
      ``[{"item_id": id, "score": s}, ...]``;
    * ``trace["scores"]`` in the same forms.

    Unknown shapes yield an empty map (scores are optional in the UI).
    """
    for key in ("recommended_item_scores", "scores", "item_scores"):
        raw = trace.get(key)
        mapped = _coerce_score_container(raw)
        if mapped:
            return mapped
    return {}


def _coerce_score_container(raw: Any) -> Dict[str, float]:
    out: Dict[str, float] = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            if isinstance(k, str) and isinstance(v, (int, float)) and not isinstance(v, bool):
                out[k] = float(v)
    elif isinstance(raw, list):
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            item_id = entry.get("item_id") or entry.get("itemId") or entry.get("id")
            score = entry.get("score")
            if isinstance(item_id, str) and isinstance(score, (int, float)) and not isinstance(score, bool):
                out[item_id] = float(score)
    return out
