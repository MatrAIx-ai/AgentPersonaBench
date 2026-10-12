from backend.service.survey_harbor_tasks import list_survey_harbor_tasks


def test_survey_harbor_task_summary_dict_is_lightweight():
    tasks = list_survey_harbor_tasks()
    assert tasks
    payload = tasks[0].to_summary_dict()
    assert payload["id"]
    assert payload["taskPath"]
    assert "profileMarkdown" not in payload
    assert "questionnaire" not in payload
    assert "instructionMarkdown" not in payload
