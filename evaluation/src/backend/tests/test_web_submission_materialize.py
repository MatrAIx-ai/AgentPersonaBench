"""Tests for task-agnostic final_answer hand-in helpers."""

from __future__ import annotations

import json
from types import SimpleNamespace

from matraix.agents.persona.cua_submission import (
    extract_final_answer_text,
    materialize_final_answer_file,
    parse_json_payload,
)


def test_parse_json_payload_uses_first_object_when_agent_keeps_talking() -> None:
    first = {"ticker": "MU", "sentiment": "buy", "confidence": 7}
    second = {"ticker": "MU", "sentiment": "hold", "confidence": 4}
    text = (
        "Here is my answer:\n"
        f"```json\n{json.dumps(first, indent=2)}\n```\n\n"
        "Wait, let me reconsider...\n"
        f"```json\n{json.dumps(second, indent=2)}\n```\n"
    )
    assert parse_json_payload(text) == first


def test_extract_final_answer_text_prefers_last_agent_message() -> None:
    trajectory = {
        "steps": [
            {"source": "agent", "message": "still researching"},
            {
                "source": "agent",
                "message": '```json\n{"ticker": "MU", "sentiment": "buy"}\n```',
            },
        ]
    }
    assert '"sentiment": "buy"' in extract_final_answer_text(trajectory)


def test_materialize_final_answer_file_writes_host_and_env(tmp_path) -> None:
    import asyncio

    logs_dir = tmp_path / "agent"
    logs_dir.mkdir()
    answer = '```json\n{"ticker": "MU", "sentiment": "buy"}\n```'
    (logs_dir / "trajectory.json").write_text(
        json.dumps(
            {"steps": [{"source": "agent", "message": answer}]}
        ),
        encoding="utf-8",
    )

    writes: list[str] = []

    class _Env:
        async def exec(self, command: str, timeout_sec: int = 30):
            writes.append(command)
            return SimpleNamespace(return_code=0, stderr="")

    ok = asyncio.run(materialize_final_answer_file(_Env(), logs_dir))
    assert ok is True
    assert (logs_dir / "final_answer.txt").read_text(encoding="utf-8") == answer
    assert any("/app/output/final_answer.txt" in cmd for cmd in writes)
    assert any("/logs/agent/final_answer.txt" in cmd for cmd in writes)
