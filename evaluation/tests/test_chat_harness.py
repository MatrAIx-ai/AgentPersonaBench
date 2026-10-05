from __future__ import annotations

from copy import deepcopy

import chat_harness


def test_prompt_bot_uses_shared_provider_client_and_keeps_history(monkeypatch):
    calls = []
    replies = iter(["first reply", "second reply"])

    def fake_chat(messages, **kwargs):
        calls.append((deepcopy(messages), dict(kwargs)))
        return next(replies)

    monkeypatch.setattr(chat_harness, "chat", fake_chat)
    session = chat_harness.PromptBotSession(
        "bot system prompt", "gpt-5.6-sol", temperature=0.6
    )

    assert session.run_turn_sync("first message") == {
        "assistantMessage": "first reply",
        "items": [],
    }
    assert session.run_turn_sync("second message") == {
        "assistantMessage": "second reply",
        "items": [],
    }

    assert calls == [
        (
            [
                {"role": "system", "content": "bot system prompt"},
                {"role": "user", "content": "first message"},
            ],
            {"model": "gpt-5.6-sol", "max_tokens": 1024, "temperature": 0.6},
        ),
        (
            [
                {"role": "system", "content": "bot system prompt"},
                {"role": "user", "content": "first message"},
                {"role": "assistant", "content": "first reply"},
                {"role": "user", "content": "second message"},
            ],
            {"model": "gpt-5.6-sol", "max_tokens": 1024, "temperature": 0.6},
        ),
    ]
