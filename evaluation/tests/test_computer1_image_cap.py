"""computer-1 trims old screenshots once the history exceeds the per-request image cap,
even when a long-context model is nowhere near its token limit (OpenAI rejects >50 images)."""
from __future__ import annotations

import asyncio
import logging
import sys

import pytest

if sys.version_info < (3, 12):
    pytest.skip("harbor needs Python 3.12", allow_module_level=True)

from harbor.agents.computer_1 import compaction as C  # noqa: E402


class _LLM:
    def get_model_context_limit(self):
        return 10_000_000  # never the reason to compact


class _Chat:
    def __init__(self, n):
        img = {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}}
        self.messages = [{"role": "user", "content": [{"type": "text", "text": f"step {i}"}, img]}
                         for i in range(n)]


def _compactor():
    async def fresh():
        return "prompt"
    return C.Computer1Compactor(_LLM(), "m", logging.getLogger("t"), fresh,
                                lambda *a: None, proactive_free_tokens=1000,
                                unwind_target_free_tokens=2000)


def test_history_over_the_cap_keeps_only_the_latest_screenshots():
    chat = _Chat(C.MAX_SCREENSHOTS_IN_HISTORY + 5)
    asyncio.run(_compactor().maybe_proactively_compact(chat, "p", "i"))
    assert C._count_image_parts(chat.messages) == C.KEEP_LAST_SCREENSHOTS
    assert all(any(p.get("type") == "image_url" for p in m["content"]) for m in chat.messages[-C.KEEP_LAST_SCREENSHOTS:])


def test_history_under_the_cap_is_untouched():
    chat = _Chat(C.MAX_SCREENSHOTS_IN_HISTORY)
    asyncio.run(_compactor().maybe_proactively_compact(chat, "p", "i"))
    assert C._count_image_parts(chat.messages) == C.MAX_SCREENSHOTS_IN_HISTORY


def test_generic_dialect_rescales_gemini_grid_coordinates():
    from harbor.agents.computer_1.providers import generic as G
    from harbor.agents.computer_1.runtime import ComputerAction

    a = ComputerAction(type="click", x=539, y=712)
    b = G._denormalize(a, 1280, 900)
    assert (b.x, b.y) == (690, 641)
    assert G._uses_normalized_coordinates("vertex_ai/gemini-3.8-flash")
    assert not G._uses_normalized_coordinates("openai/gpt-6-sol")
