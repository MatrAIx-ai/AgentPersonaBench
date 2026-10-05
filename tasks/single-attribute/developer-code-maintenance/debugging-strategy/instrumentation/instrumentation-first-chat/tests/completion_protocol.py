"""Host-owned passage provenance; semantic completion remains the judge's task."""
from __future__ import annotations

import json
import re

REVISION = "6.0"
MAX_QUOTE = 12_000  # Same bound as a validated persona turn.
FINAL_TURNS = {"Receipt adjustment": 10, "Group summary": 11, "Duplicate normalization": 12}
FIELDS = ("endorsement", "action", "check_operation", "check_target", "post_change")
STATES = ("SUPPORTED", "ABSENT")
STATUSES = ("COMPLETE", "INCOMPLETE")
ORDERS = ("CHECK_BEFORE_CHANGE", "CHANGE_BEFORE_CHECK", "NO_COMMITTED_CHECK", "ORDER_NOT_ESTABLISHED")
CITATION = {
    "type": "string",
    "description": "One exact passage ID from the host evidence catalog, such as T10.S02. Never write a quotation or a separate turn number.",
}
CRITERION = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "state": {"type": "string", "enum": list(STATES)},
        "evidence": {"type": "array", "items": CITATION,
                     "description": "Zero to two distinct passage IDs. SUPPORTED needs evidence."},
    },
    "required": ["state", "evidence"],
}
RELATION = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "operation": {"type": "array", "items": CITATION,
                      "description": "Zero to two distinct IDs selected from check_operation.evidence, identifying the same checking occurrence."},
        "change": {"type": "array", "items": CITATION,
                   "description": "Zero to two distinct passage IDs identifying the proposed change."},
        "evidence": {"type": "array", "items": CITATION,
                     "description": "Zero to two distinct passage IDs establishing the temporal relation. Source order alone does not establish action order."},
        "order": {"type": "string", "enum": list(ORDERS)},
    },
    "required": ["operation", "change", "evidence", "order"],
}
COMPLETION_TOOL = {
    "name": "record_completion_evidence",
    "description": "Record evidence for five independent completion criteria, without an overall verdict.",
    "strict": True,
    "input_schema": {
        "type": "object", "additionalProperties": False,
        "properties": {
            "incident": {"type": "string", "enum": list(FINAL_TURNS)},
            **{name: CRITERION for name in FIELDS[:-1]},
            "post_change": RELATION,
        },
        "required": ["incident", *FIELDS],
    },
}

_LIST_ITEM = re.compile(r"^[ \t]*(?:[-*+]|\d+[.)]|\(\d+\))[ \t]+")
_FENCE = re.compile(r"^[ \t]*(`{3,}|~{3,})")


def _blocks(text):
    """Preserve physical list items and fenced code; join wrapped prose lines."""
    start = offset = 0
    kind = "prose"
    fence = None
    for line in text.splitlines(keepends=True):
        marker = _FENCE.match(line)
        if fence is not None:
            offset += len(line)
            if (marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence)
                    and not line[marker.end():].strip()):
                yield start, offset, "code"
                start, kind, fence = offset, "prose", None
            continue
        if marker:
            if start < offset:
                yield start, offset, kind
            start, kind, fence = offset, "code", marker[1]
        elif _LIST_ITEM.match(line):
            if start < offset:
                yield start, offset, kind
            start, kind = offset, "list"
        offset += len(line)
        if fence is None and not line.strip():
            yield start, offset, kind
            start, kind = offset, "prose"
    if start < offset:
        yield start, offset, kind


def _sentence_ends(text, start, end):
    """Conservative punctuation boundaries, never inside an inline code span."""
    i = start
    while i < end:
        if text[i] == "`":
            j = i + 1
            while j < end and text[j] == "`":
                j += 1
            closing = text.find(text[i:j], j, end)
            if closing != -1:
                i = closing + j - i
                continue
        if text[i] in ".!?。！？":
            j = i + 1
            while j < end and text[j] in "\"'”’)]}":
                j += 1
            if j == end or text[j].isspace():
                # Decimal points already fail the whitespace test. Keep dotted
                # abbreviations together instead of splitting after e.g./i.e.
                if text[i] != "." or not re.search(r"(?:[A-Za-z]\.){2,}$", text[start:i + 1]):
                    while j < end and text[j].isspace():
                        j += 1
                    yield j
                    i = j
                    continue
        i += 1
    yield end


def evidence_catalog(turns):
    """Ordered lossless passages; offsets count Unicode code points, not bytes.

    IDs identify source passages only. Their existence, numeric order, or text
    does not establish endorsement, semantic relevance, or temporal ordering.
    """
    if not isinstance(turns, list) or not 1 <= len(turns) <= 12:
        raise ValueError("evidence catalog needs one to twelve persona turns")
    catalog = []
    for number, text in enumerate(turns, 1):
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_QUOTE:
            raise ValueError("evidence catalog contains an invalid persona turn")
        spans = []
        for start, end, kind in _blocks(text):
            cursor = start
            boundaries = _sentence_ends(text, start, end) if kind == "prose" else (end,)
            for stop in boundaries:
                if stop > cursor:
                    if not text[cursor:stop].strip() and spans:
                        spans[-1] = (spans[-1][0], stop)
                    else:
                        spans.append((cursor, stop))
                    cursor = stop
        if len(spans) > 1 and not text[spans[0][0]:spans[0][1]].strip():
            spans[1] = (spans[0][0], spans[1][1])
            spans.pop(0)
        for index, (start, end) in enumerate(spans, 1):
            catalog.append({"id": f"T{number}.S{index:02d}", "turn": number,
                            "start": start, "end": end, "text": text[start:end]})
    return catalog


def strict_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate completion response key")
            result[key] = value
        return result
    if not isinstance(raw, str) or len(raw) > 12000:
        raise ValueError("invalid completion response text")
    try:
        return json.loads(raw, object_pairs_hook=unique)
    except (ValueError, RecursionError) as exc:
        raise ValueError("completion response must be one strict JSON object") from exc


def validate_report(report, incident, turns):
    if not isinstance(incident, str) or incident not in FINAL_TURNS:
        raise ValueError("unknown completion incident")
    if not isinstance(report, dict) or set(report) != {"incident", *FIELDS}:
        raise ValueError("completion criteria have missing or extra fields")
    if report["incident"] != incident:
        raise ValueError("completion criteria do not match the requested incident")
    catalog = {entry["id"]: entry for entry in evidence_catalog(turns)}

    def resolve(ids):
        if not isinstance(ids, list) or len(ids) > 2:
            raise ValueError("completion passage IDs must be a bounded array")
        if any(not isinstance(item, str) or item not in catalog for item in ids):
            raise ValueError("completion evidence contains an unknown passage ID")
        if len(set(ids)) != len(ids):
            raise ValueError("completion passage IDs must be distinct")
        return [{"id": item, "turn": catalog[item]["turn"],
                 "start": catalog[item]["start"], "end": catalog[item]["end"],
                 "quote": catalog[item]["text"]} for item in ids]

    states, criteria = [], {}
    for field in FIELDS[:-1]:
        criterion = report[field]
        if not isinstance(criterion, dict) or set(criterion) != {"state", "evidence"}:
            raise ValueError("completion criterion fields are invalid")
        state, citations = criterion["state"], criterion["evidence"]
        if not isinstance(state, str) or state not in STATES:
            raise ValueError("unknown completion criterion state")
        resolved = resolve(citations)
        if state != "ABSENT" and not citations:
            raise ValueError("supported criterion lacks evidence")
        states.append(state)
        criteria[field] = {"state": state, "evidence": resolved}
    relation = report["post_change"]
    if not isinstance(relation, dict) or set(relation) != {"operation", "change", "evidence", "order"}:
        raise ValueError("completion temporal relation fields are invalid")
    order = relation["order"]
    if not isinstance(order, str) or order not in ORDERS:
        raise ValueError("unknown completion temporal order")
    resolved_relation = {field: resolve(relation[field]) for field in ("operation", "change", "evidence")}
    references = relation["operation"]
    if any(item not in report["check_operation"]["evidence"] for item in references):
        raise ValueError("temporal operation reference is outside the checking evidence")
    operation_state = report["check_operation"]["state"]
    if order == "NO_COMMITTED_CHECK" and operation_state == "SUPPORTED":
        raise ValueError("temporal relation contradicts the supported checking operation")
    if order in ("CHECK_BEFORE_CHANGE", "CHANGE_BEFORE_CHECK"):
        if operation_state == "ABSENT":
            raise ValueError("definite temporal order contradicts an absent checking operation")
        if not all(relation[field] for field in ("operation", "change", "evidence")):
            raise ValueError("temporal order lacks operation, change or relation evidence")
    criteria["post_change"] = {"operation": list(references),
                               "change": resolved_relation["change"],
                               "evidence": resolved_relation["evidence"], "order": order}
    states.append("SUPPORTED" if order == "CHANGE_BEFORE_CHECK" else "ABSENT")
    status = "COMPLETE" if all(state == "SUPPORTED" for state in states) else "INCOMPLETE"
    return {"incident": incident, "status": status, "criteria": criteria,
            "protocol_revision": REVISION}


def parse_tool_response(content, stop_reason):
    if stop_reason != "tool_use" or not isinstance(content, list) or len(content) != 1:
        raise ValueError("completion judge must return one complete tool call")
    block = content[0]
    if not isinstance(block, dict) or block.get("type") != "tool_use":
        raise ValueError("completion judge returned non-tool content")
    if block.get("name") != COMPLETION_TOOL["name"] or not isinstance(block.get("id"), str) or not block["id"]:
        raise ValueError("completion judge returned an unknown or unidentified tool")
    return block.get("input")
