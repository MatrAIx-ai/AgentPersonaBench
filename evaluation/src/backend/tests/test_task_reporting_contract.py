from __future__ import annotations

import json
from pathlib import Path


def test_all_application_tasks_define_reporting_json() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    tasks_dir = repo_root / "application" / "tasks"
    task_dirs = sorted(path.parent for path in tasks_dir.glob("*/task.toml"))
    assert task_dirs, "expected application tasks to exist"

    for task_dir in task_dirs:
        reporting_path = task_dir / "reporting.json"
        assert reporting_path.is_file(), "{} is missing".format(reporting_path)
        payload = json.loads(reporting_path.read_text(encoding="utf-8"))
        assert payload.get("schemaVersion") == "1.0", "{} must declare schemaVersion".format(
            reporting_path
        )
        assert isinstance(
            payload.get("contextRules"), list
        ), "{} must contain contextRules[]".format(reporting_path)
