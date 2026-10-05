"""Legacy iOS notification-decision materializer (schema-specific).

macOS/iOS use.computer tasks now default to task-agnostic
``materialize_final_answer_file`` + host_verifier / test.sh recovery.
This module remains for older notification-decision schemas that still
call it explicitly.
"""

from __future__ import annotations

from typing import Any
from pathlib import Path

from matraix.agents.persona.cua_submission import (
    extract_ios_decision_from_trajectory,
    materialize_json_file,
)

__all__ = [
    "extract_ios_decision_from_trajectory",
    "materialize_ios_decision_file",
]


async def materialize_ios_decision_file(
    environment: Any,
    logs_dir: Path,
    *,
    output_path: str = "/app/output/decision.json",
    logger: Any | None = None,
) -> bool:
    """Write decision.json on the simulator host from trajectory `done` tool output."""
    return await materialize_json_file(
        environment,
        logs_dir,
        extractor=extract_ios_decision_from_trajectory,
        output_path=output_path,
        logger=logger,
        log_label="ios submission",
    )
