from backend.service.example_task_catalog import categorize_task, discover_example_tasks, discover_survey_application_tasks
from backend.service.survey_harbor_tasks import list_survey_harbor_tasks
from backend.service.web_tasks import list_web_eval_tasks
from backend.service.os_app_tasks import list_os_app_eval_tasks


def test_discover_example_tasks_by_category():
    survey = discover_example_tasks(category="survey")
    web = discover_example_tasks(category="web")
    cua = discover_example_tasks(category="os-app")
    assert len(survey) == 1
    assert survey[0].folder_name == "example-survey_product-feedback"
    assert any("example-survey_" in task.folder_name for task in survey)
    assert any("example-web-playwright_" in task.folder_name for task in web)
    assert any("example-web-cua_" in task.folder_name for task in web)
    assert any("example-computer-use-" in task.folder_name for task in cua)
    assert not any("example-web-cua" in task.folder_name for task in cua)


def test_categorize_task():
    assert categorize_task("example-survey_product-feedback", "survey") == "survey"
    assert categorize_task("survey_nike-air-max-dn", "survey") == "survey"
    assert categorize_task("example-web-playwright_quote-choice", "web") == "web"
    assert categorize_task("example-web-cua_bookshop-choice", "web") == "web"
    assert categorize_task("example-computer-use-linux_note-to-csv", "os-app") == "os-app"


def test_list_survey_harbor_tasks_includes_product_feedback():
    tasks = list_survey_harbor_tasks()
    match = [task for task in tasks if task.task_path.endswith("example-survey_product-feedback")]
    assert match
    assert match[0].instrument_id == "product_feedback_v1"
    assert match[0].survey_kind == "example"


def test_discover_survey_application_tasks_includes_contributing_tasks():
    records = discover_survey_application_tasks()
    assert len(records) >= 6
    folders = {record.folder_name for record in records}
    assert "example-survey_product-feedback" in folders
    assert "survey_nike-air-max-dn" in folders
    assert "example-survey_nike-air-max-dn" not in folders


def test_list_web_eval_tasks_includes_example_web_tasks():
    tasks = list_web_eval_tasks()
    ids = {task.id for task in tasks}
    assert "web-playwright-quote-choice" in ids
    assert "web-cua-bookshop-choice" in ids


def test_list_web_eval_tasks_includes_ikea_room_planner():
    tasks = {task.id: task for task in list_web_eval_tasks()}
    ikea = tasks.get("web-ikea-room-planner")
    assert ikea is not None
    assert ikea.output_artifact == "room_plan.json"
    assert ikea.submission_profile == "room_plan"
    assert ikea.site_url.startswith("https://www.ikea.com/")


def test_list_os_app_eval_tasks_includes_computer_use_only():
    tasks = list_os_app_eval_tasks()
    ids = {task.id for task in tasks}
    assert "computer-use-linux-note-to-csv" in ids
    assert "web-cua-bookshop-choice" not in ids
