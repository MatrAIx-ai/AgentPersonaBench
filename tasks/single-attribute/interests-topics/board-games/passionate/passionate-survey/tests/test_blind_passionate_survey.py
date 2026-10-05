"""Offline checks of exact prompt omission and production scoring."""
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest

TASK = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("borrowing_survey_blind", TASK / "tests/run_blind.py")
BLIND = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BLIND)


def test_prompt_is_exact_instruction_and_questionnaire_only():
    prompt = BLIND.build_prompt()
    assert prompt == ((TASK / "instruction.md").read_text() + "\n\n"
                      + (TASK / "input/questionnaire.yaml").read_text())
    assert "topic_board_games" not in prompt
    assert "# Your profile" not in prompt
    assert "Passionate" not in prompt


def test_every_reply_uses_production_verifier(tmp_path):
    for name, choices, expected in (
        ("held", ("p47", "f36", "h48", "d28"), "HELD"),
        ("jigsaw", ("p18", "f52", "h65", "d91"), "VIOLATED"),
        ("wrong-hold", ("p47", "f36", "h65", "d28"), "VIOLATED"),
    ):
        directory = tmp_path / name
        directory.mkdir()
        raw = json.dumps({"answers": [
            {"questionId": q, "selectedOptionId": o}
            for q, o in zip(("primary", "fallback", "hold", "digest"), choices)
        ]})
        scored = BLIND.score_reply(directory, raw)
        assert scored["verdict"] == expected
        assert (directory / "survey_result.json").read_text() == raw
    malformed = tmp_path / "malformed"
    malformed.mkdir()
    assert BLIND.score_reply(malformed, "I need more details.")["verdict"] == "VIOLATED"


@pytest.mark.parametrize("template,copies", [
    ("{json}", 1), ("Here is my plan:\n{json}\nThanks.", 1),
    ("```json\n{json}\n```", 1),
    ("My choice:\n```json\n{json}\n```\nThe file:\n```json\n{json}\n```", 2),
])
def test_transport_preserves_literal_ids_even_when_nonadherent(template, copies):
    document = {"answers": [
        {"questionId": q, "selectedOptionId": o}
        for q, o in zip(("primary", "fallback", "hold", "digest"), ("p18", "f52", "h65", "d91"))
    ]}
    actual, count = BLIND.extract_submission(template.replace("{json}", json.dumps(document)))
    assert actual == document
    assert count == copies


@pytest.mark.parametrize("raw", [
    "", "no choice", "[]", '[{"answers":[]}]', '{"broken": {"answers":[]}',
    '{"answers":[],"answers":[]}', '{"answers":[]} {"answers":[1]}',
    "```json\n[]\n```", "```json\n{}",
    "```json\n{}\n```\n{\"other\":1}", " " * 65537,
])
def test_transport_rejects_malformed_or_ambiguous_replies(raw):
    with pytest.raises(ValueError):
        BLIND.extract_submission(raw)


@pytest.mark.parametrize("source_changes", [False, True])
def test_fixed_batch_records_parameters_and_rejects_source_drift(tmp_path, monkeypatch, source_changes):
    """Exercise orchestration without a provider; still call the real verifier."""
    calls = []
    document = {"answers": [
        {"questionId": q, "selectedOptionId": o}
        for q, o in zip(("primary", "fallback", "hold", "digest"), ("p18", "f52", "h65", "d91"))
    ]}

    def fake_chat(messages, **kwargs):
        calls.append((messages, kwargs))
        return json.dumps(document)

    monkeypatch.setitem(sys.modules, "llm_client", SimpleNamespace(chat=fake_chat))
    monkeypatch.setitem(sys.modules, "usage", SimpleNamespace(reset=lambda: None, summary=lambda: {"calls": 1}))
    monkeypatch.setattr(os, "environ", os.environ.copy())
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setattr(sys, "argv", ["run_blind.py", "--output", str(tmp_path / "batch"), "--runs", "3"])
    if source_changes:
        snapshots = iter([{"input": "before"}, {"input": "changed"}])
        monkeypatch.setattr(BLIND, "source_hashes", lambda: next(snapshots))
        with pytest.raises(SystemExit, match="task changed"):
            BLIND.main()
    else:
        BLIND.main()

    summary = json.loads((tmp_path / "batch/control_summary.json").read_text())
    assert len(calls) == 3
    assert all(messages == [{"role": "user", "content": BLIND.build_prompt()}] for messages, _ in calls)
    assert all(kwargs["max_tokens"] == summary["max_tokens_requested"] == 2000 for _, kwargs in calls)
    assert all(kwargs["temperature"] == summary["temperature_requested"] for _, kwargs in calls)
    assert summary["source_unchanged"] is (not source_changes)
    assert summary["finished_utc"]
    assert summary["responded"] == summary["completed"] == 3
    assert summary["passes"] == 0
