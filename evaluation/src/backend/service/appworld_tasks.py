"""Built-in AppWorld task registry for Playground."""

from __future__ import annotations

from backend.service.appworld_types import AppWorldEvalTask


_APPWORLD_TASKS = [
    AppWorldEvalTask(
        id="appworld-demo-personal-admin",
        title="AppWorld personal admin task",
        app_name="AppWorld",
        description=(
            "Complete a multi-app personal administration task through "
            "AppWorld-style APIs and report the final state."
        ),
    )
]


def list_appworld_eval_tasks() -> list[AppWorldEvalTask]:
    """Return the AppWorld tasks exposed by Playground."""
    return list(_APPWORLD_TASKS)


def get_appworld_eval_task(task_id: str) -> AppWorldEvalTask:
    """Return one AppWorld task by id."""
    for task in _APPWORLD_TASKS:
        if task.id == task_id:
            return task
    raise KeyError("unknown AppWorld task: {}".format(task_id))
