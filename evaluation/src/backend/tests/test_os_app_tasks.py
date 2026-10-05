from backend.service.os_app_tasks import get_os_app_eval_task, list_os_app_eval_tasks


def test_list_os_app_eval_tasks_includes_harbor_computer_use_tasks():
    tasks = list_os_app_eval_tasks()
    ids = {task.id for task in tasks}
    assert "computer-use-linux-note-to-csv" in ids
    assert "computer-use-macos-calendar-reminder-handoff" in ids
    assert "computer-use-ios-photo-access-review" in ids
    assert "os-app-ios-news-subscription-decision" in ids
    assert "os-app-macos-shortcuts-gallery-picks" in ids
    assert all(task.meta_type == "os-app" for task in tasks)


def test_get_os_app_eval_task_linux_has_os_metadata():
    task = get_os_app_eval_task("computer-use-linux-note-to-csv")
    assert task.os == "linux"
    assert task.platform == "linux"
    assert task.os_app_backend == "docker"
