from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from playground.types import (
    Persona, PlaygroundConfig, PlaygroundResult,
)


def run_playground(
    session: Any,
    persona: Persona,
    sut_description: str,
    config: PlaygroundConfig,
    simulator: Any | None = None,
    *,
    created_at: str,
    on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
    task_path: Optional[str] = None,
    persona_yaml_path: Optional[str] = None,
    repo_root: Optional[Any] = None,
) -> PlaygroundResult:
    del simulator
    from playground.user_sim.runner import run_playground as _run_user_sim

    return _run_user_sim(
        session,
        persona,
        sut_description,
        config,
        created_at=created_at,
        on_event=on_event,
        task_path=task_path,
        persona_yaml_path=persona_yaml_path,
        repo_root=repo_root,
    )
