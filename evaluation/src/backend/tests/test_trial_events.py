"""Tests for Harbor trial NDJSON event streams."""

from __future__ import annotations

from pathlib import Path

from playground.harbor.trial_events import (
    TrialEventWriter,
    read_events_after,
)


def test_trial_event_writer_and_incremental_read(tmp_path: Path) -> None:
    events_path = tmp_path / "trial-0" / "events.jsonl"
    writer = TrialEventWriter(events_path)

    writer.append({"type": "phase", "phase": "persona_kickoff"})
    writer.append({"type": "turn", "turn": {"turnIndex": 1, "userMessage": "hi", "assistantMessage": "hello"}})

    first, offset = read_events_after(events_path, 0)
    assert len(first) == 2
    assert first[0]["phase"] == "persona_kickoff"
    assert first[1]["turn"]["assistantMessage"] == "hello"

    writer.append({"type": "phase", "phase": "persona_thinking"})
    second, offset = read_events_after(events_path, offset)
    assert len(second) == 1
    assert second[0]["phase"] == "persona_thinking"

    all_events, _ = read_events_after(events_path, 0)
    assert len(all_events) == 3


def test_read_events_after_missing_file(tmp_path: Path) -> None:
    events, offset = read_events_after(tmp_path / "missing.jsonl", 0)
    assert events == []
    assert offset == 0
