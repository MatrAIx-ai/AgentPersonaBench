from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Union


@dataclass(frozen=True)
class WebEvalTask:
    id: str
    title: str
    site_name: str
    site_url: str
    task_path: Union[str, Path]
    description: str
    meta_type: str = ""
    domain: str = ""
    difficulty: str = "easy"
    task_kind: str = "task"
    tags: tuple[str, ...] = ()
    output_artifact: str = "web_result.json"
    submission_profile: str = "web_result"

    def to_summary_dict(self) -> Dict[str, Any]:
        """List-endpoint payload (no markdown bodies)."""
        return self.to_dict()

    def to_dict(self) -> Dict[str, Any]:
        task_path = self.task_path
        if isinstance(task_path, Path):
            parts = task_path.parts
            if "application" in parts and "tasks" in parts:
                idx = parts.index("tasks")
                task_path = "/".join(parts[idx - 1 :])
            else:
                task_path = str(task_path)
        return {
            "id": self.id,
            "title": self.title,
            "siteName": self.site_name,
            "siteUrl": self.site_url,
            "metaType": self.meta_type,
            "domain": self.domain,
            "difficulty": self.difficulty,
            "taskKind": self.task_kind,
            "tags": list(self.tags),
            "description": self.description,
            "taskPath": str(task_path),
            "outputArtifact": self.output_artifact,
            "submissionProfile": self.submission_profile,
        }
