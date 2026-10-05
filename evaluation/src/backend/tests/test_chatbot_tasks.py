from pathlib import Path

from backend.service.chatbot_tasks import get_chatbot_eval_task, list_chatbot_eval_tasks

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_list_chatbot_eval_tasks_discovers_registered_chatbot_tasks():
    tasks = list_chatbot_eval_tasks()
    ids = {task.id for task in tasks}

    assert "chat-meal-planning-nutrition" in ids
    assert "chat-openbb-corporate-action-honesty" in ids
    assert "chat-api-support-chatbot" in ids
    assert "chat-mcp-support-chatbot" in ids
    assert len(tasks) >= 4

    for task in tasks:
        task_path = REPO_ROOT / Path(str(task.task_path))
        assert task_path.is_dir(), "{} has missing task path".format(task.id)


def test_get_chatbot_eval_task_reads_runtime_defaults_from_chatbot_yaml():
    task = get_chatbot_eval_task("chat-openbb-corporate-action-honesty")

    assert task.transport == "sidecar_http"
    assert task.application_id == "finance_openbb"
    assert task.application_context == "financial_research"
    assert task.default_domain == "financial_research"
    assert task.can_start is True
    assert task.health_url == "http://127.0.0.1:8901"


def test_get_chatbot_eval_task_preserves_mcp_transport():
    task = get_chatbot_eval_task("chat-mcp-support-chatbot")

    assert task.transport == "mcp"
    assert task.application_id == "acme_support_mcp"
    assert task.can_start is True
    assert task.health_url == "http://127.0.0.1:8903"
    assert task.available in (True, False)


def test_get_chatbot_eval_task_reads_meal_planning_sidecar_defaults():
    task = get_chatbot_eval_task("chat-meal-planning-nutrition")

    assert task.transport == "sidecar_http"
    assert task.application_id == "meal_planning_nutrition"
    assert task.application_context == "meal_planning"
    assert task.default_domain == "meal_planning"


def test_get_chatbot_eval_task_reads_support_api_sidecar_defaults():
    task = get_chatbot_eval_task("chat-api-support-chatbot")

    assert task.transport == "sidecar_http"
    assert task.application_id == "acme_support_api"
    assert task.application_context == "customer_support"
    assert task.can_start is True
    assert task.health_url == "http://127.0.0.1:8904"
