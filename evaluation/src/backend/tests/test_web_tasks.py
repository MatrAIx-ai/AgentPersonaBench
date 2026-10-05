from backend.service.web_tasks import get_web_eval_task, list_web_eval_tasks
from harbor.models.task.paths import TaskPaths
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_web_task_path_is_absolute_and_environment_resolves():
    task = get_web_eval_task("web-playwright-quote-choice")
    task_path = REPO_ROOT / Path(str(task.task_path))
    environment_dir = TaskPaths.from_task_dir(task_path).environment_dir
    assert environment_dir.is_dir(), environment_dir


def test_all_registered_web_tasks_have_absolute_paths():
    for task in list_web_eval_tasks():
        task_path = REPO_ROOT / Path(str(task.task_path))
        assert task_path.is_dir(), "{} has missing task path".format(task.id)


def test_mit_ocw_course_choice_is_registered():
    task = get_web_eval_task("web-mit-ocw-course-choice")

    assert task.task_path == "application/tasks/web_mit-ocw-course-choice"
    assert task.task_kind == "task"
    assert task.site_name == "MIT OpenCourseWare"
    assert task.site_url == "https://ocw.mit.edu/search/"
    assert task.output_artifact == "course_choice.json"
    assert task.submission_profile == "course_choice"


def test_notion_plan_comparison_is_registered():
    task = get_web_eval_task("web-notion-plan-comparison")

    assert task.task_path == "application/tasks/web_notion-plan-comparison"
    assert task.task_kind == "task"
    assert task.site_name == "Notion pricing"
    assert task.site_url == "https://www.notion.com/pricing"
    assert task.output_artifact == "notion_plan_comparison.json"
    assert task.submission_profile == "notion_plan_comparison"


def test_allrecipes_recipe_choice_is_registered():
    task = get_web_eval_task("web-allrecipes-recipe-choice")

    assert task.task_path == "application/tasks/web_allrecipes-recipe-choice"
    assert task.task_kind == "task"
    assert task.site_name == "Allrecipes"
    assert task.site_url == "https://www.allrecipes.com/"
    assert task.output_artifact == "recipe_choice.json"
    assert task.submission_profile == "recipe_choice"


def test_openlibrary_book_choice_is_registered():
    task = get_web_eval_task("web-openlibrary-book-choice")

    assert task.task_path == "application/tasks/web_openlibrary-book-choice"
    assert task.task_kind == "task"
    assert task.site_name == "Open Library"
    assert task.site_url == "https://openlibrary.org/"
    assert task.output_artifact == "book_choice.json"
    assert task.submission_profile == "book_choice"
