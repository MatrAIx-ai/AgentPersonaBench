from backend.service.chatbot_tasks import list_chatbot_eval_tasks
from backend.service.os_app_tasks import list_os_app_eval_tasks
from backend.service.survey_harbor_tasks import list_survey_harbor_tasks
from backend.service.web_tasks import list_web_eval_tasks


def test_chatbot_task_summary_dict_omits_live_availability():
    tasks = list_chatbot_eval_tasks()
    assert tasks
    payload = tasks[0].to_summary_dict()
    assert payload["id"]
    assert payload["taskPath"]
    assert "available" not in payload
    assert "statusDetail" not in payload


def test_web_task_summary_dict_is_lightweight():
    tasks = list_web_eval_tasks()
    assert tasks
    payload = tasks[0].to_summary_dict()
    assert payload["id"]
    assert payload["taskPath"]
    assert "profileMarkdown" not in payload
    assert "instructionMarkdown" not in payload


def test_os_app_task_summary_dict_is_lightweight():
    tasks = list_os_app_eval_tasks()
    assert tasks
    payload = tasks[0].to_summary_dict()
    assert payload["id"]
    assert payload["taskPath"]
    assert "profileMarkdown" not in payload
    assert "instructionMarkdown" not in payload


def test_survey_task_summary_dict_is_lightweight():
    tasks = list_survey_harbor_tasks()
    assert tasks
    payload = tasks[0].to_summary_dict()
    assert payload["id"]
    assert payload["taskPath"]
    assert "profileMarkdown" not in payload
    assert "questionnaire" not in payload
