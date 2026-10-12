"""Playground OS app (computer-use) task types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class OsAppEvalTask:
    id: str
    title: str
    platform: str
    description: str
    task_path: str
    meta_type: str = ""
    os: str = ""
    domain: str = ""
    difficulty: str = "easy"
    task_kind: str = "task"
    tags: tuple[str, ...] = ()
    output_artifact: str = "decision.json"
    os_app_submission_profile: Optional[str] = None
    environment_label: str = "Docker · persona-computer-1"
    os_app_backend: str = "docker"

    def to_summary_dict(self) -> Dict[str, Any]:
        """List-endpoint payload (no markdown bodies)."""
        return self.to_dict()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "platform": self.platform,
            "metaType": self.meta_type,
            "os": self.os,
            "domain": self.domain,
            "difficulty": self.difficulty,
            "taskKind": self.task_kind,
            "tags": list(self.tags),
            "description": self.description,
            "taskPath": self.task_path,
            "outputArtifact": self.output_artifact,
            "osAppSubmissionProfile": self.os_app_submission_profile,
            "environmentLabel": self.environment_label,
            "osAppBackend": self.os_app_backend,
        }
