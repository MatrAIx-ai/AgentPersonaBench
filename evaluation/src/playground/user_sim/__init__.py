"""Tool-driven multi-turn simulated user."""

from __future__ import annotations


def run_playground(*args, **kwargs):
    from playground.user_sim.runner import run_playground as _run_playground

    return _run_playground(*args, **kwargs)


async def run_playground_async(*args, **kwargs):
    from playground.user_sim.runner import (
        run_playground_async as _run_playground_async,
    )

    return await _run_playground_async(*args, **kwargs)


__all__ = [
    "run_playground",
    "run_playground_async",
]
