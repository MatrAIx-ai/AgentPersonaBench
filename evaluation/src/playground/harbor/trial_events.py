"""Append-only NDJSON event stream for live Harbor trial monitoring."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

EVENTS_FILENAME = "events.jsonl"


class TrialEventWriter:
    """Write one JSON object per line to ``events.jsonl`` under a trial directory."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def for_trial_dir(cls, trial_dir: Path) -> "TrialEventWriter":
        return cls(trial_dir / EVENTS_FILENAME)

    def append(self, event: dict[str, Any]) -> None:
        line = json.dumps(event, ensure_ascii=False)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()


def read_events_after(path: Path, after: int = 0) -> tuple[list[dict[str, Any]], int]:
    """Return newly complete event lines after a byte ``after`` offset."""
    if not path.is_file():
        return [], 0
    text = path.read_text(encoding="utf-8")
    consumed = max(0, min(after, len(text)))
    if consumed >= len(text):
        return [], consumed

    events: list[dict[str, Any]] = []
    while consumed < len(text):
        newline = text.find("\n", consumed)
        if newline == -1:
            break
        line = text[consumed:newline]
        consumed = newline + 1
        stripped = line.strip()
        if stripped:
            events.append(json.loads(stripped))
    return events, consumed
