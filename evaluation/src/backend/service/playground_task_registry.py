"""Playground task index — maintained by Playground, not task contributors.

Contributors declare Harbor-standard metadata in ``task.toml`` (``metadata.type``,
``metadata.os`` for OS app tasks, ``domain``, ``difficulty``, ``tags``). This registry only
answers Playground questions: which cockpit a task belongs in, example vs task, and
eval-runtime overrides that Harbor metadata does not cover.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class PlaygroundTaskEntry:
    application_type: str
    task_kind: Optional[str] = None
    site_name: str = ""
    site_url: str = ""
    output_artifact: str = ""
    submission_profile: str = ""
    os_app_backend: str = ""
    os_app_platform: str = ""
    environment_label: str = ""
    os_app_submission_profile: Optional[str] = None


def default_task_kind(folder_name: str) -> str:
    return "example" if folder_name.startswith("example-") else "task"


def resolve_task_kind(folder_name: str, entry: PlaygroundTaskEntry) -> str:
    return default_task_kind(folder_name)


# folder name → Playground routing overrides (site URLs, OS backends, etc.).
# Tasks with ``metadata.type`` in task.toml are auto-discovered when not listed here.
PLAYGROUND_TASK_INDEX: Dict[str, PlaygroundTaskEntry] = {
    # OS app (computer-use)
    "example-computer-use-linux_note-to-csv": PlaygroundTaskEntry(
        application_type="os-app",
        os_app_backend="docker",
        os_app_platform="linux",
        environment_label="Docker Xvfb · persona-computer-1",
    ),
    "example-computer-use-macos_calendar-reminder-handoff": PlaygroundTaskEntry(
        application_type="os-app",
        os_app_backend="macos",
        os_app_platform="macos",
        environment_label="use.computer · persona-computer-1",
    ),
    "example-computer-use-ios_photo-access-review": PlaygroundTaskEntry(
        application_type="os-app",
        os_app_backend="ios",
        os_app_platform="ios",
        environment_label="use.computer iOS · persona-computer-1",
    ),
    "os-app-ios_news-subscription-decision": PlaygroundTaskEntry(
        application_type="os-app",
        os_app_backend="ios",
        os_app_platform="ios",
        environment_label="use.computer iOS · persona-computer-1",
        output_artifact="decision.json",
    ),
    "os-app-macos_shortcuts-gallery-picks": PlaygroundTaskEntry(
        application_type="os-app",
        os_app_backend="macos",
        os_app_platform="macos",
        environment_label="use.computer · persona-computer-1",
        output_artifact="picks.json",
    ),
    "os-app-macos_stocks-mu-sentiment": PlaygroundTaskEntry(
        application_type="os-app",
        os_app_backend="macos",
        os_app_platform="macos",
        environment_label="use.computer · persona-computer-1",
        output_artifact="sentiment.json",
    ),
    # Web
    "example-web-playwright_quote-choice": PlaygroundTaskEntry(
        application_type="web",
        site_name="quotes.toscrape.com",
        site_url="https://quotes.toscrape.com/",
        output_artifact="quote_choice.json",
        submission_profile="quote_choice",
    ),
    "example-web-browser-use_laptop-choice": PlaygroundTaskEntry(
        application_type="web",
        site_name="webscraper.io laptops",
        site_url="https://webscraper.io/test-sites/e-commerce/static/computers/laptops",
        output_artifact="laptop_choice.json",
        submission_profile="laptop_choice",
    ),
    "example-web-cocoa_plan-choice": PlaygroundTaskEntry(
        application_type="web",
        site_name="PythonAnywhere pricing",
        site_url="https://www.pythonanywhere.com/pricing/",
        output_artifact="plan_choice.json",
        submission_profile="plan_choice",
    ),
    "example-web-cua_bookshop-choice": PlaygroundTaskEntry(
        application_type="web",
        site_name="books.toscrape.com",
        site_url="https://books.toscrape.com/",
        output_artifact="book_interest.json",
        submission_profile="book_interest",
    ),
    "web_ikea-room-planner": PlaygroundTaskEntry(
        application_type="web",
        site_name="IKEA Room Planner",
        # The trailing `#<design-id>/<scene-id>` fragment is required: without it
        # the planner hangs on "Preparing your room ..." forever, because it has
        # no scene to load. Do not trim it to the bare ?roomType=generic URL.
        site_url=(
            "https://www.ikea.com/us/en/home-design/room/?roomType=generic"
            "#1d9a5bb8-08b5-43aa-ab0c-ff91d92c95f9/0943b0b9-198c-4e74-b287-171db3f4ad35"
        ),
        output_artifact="room_plan.json",
        submission_profile="room_plan",
    ),
    "web_portfoliovisualizer-backtest-allocation": PlaygroundTaskEntry(
        application_type="web",
        site_name="Portfolio Visualizer",
        site_url="https://www.portfoliovisualizer.com/backtest-portfolio",
        output_artifact="portfolio_backtest.json",
        submission_profile="portfolio_backtest",
    ),
    "web_mit-ocw-course-choice": PlaygroundTaskEntry(
        application_type="web",
        site_name="MIT OpenCourseWare",
        site_url="https://ocw.mit.edu/search/",
        output_artifact="course_choice.json",
        submission_profile="course_choice",
    ),
    "web_notion-plan-comparison": PlaygroundTaskEntry(
        application_type="web",
        site_name="Notion pricing",
        site_url="https://www.notion.com/pricing",
        output_artifact="notion_plan_comparison.json",
        submission_profile="notion_plan_comparison",
    ),
    "web_allrecipes-recipe-choice": PlaygroundTaskEntry(
        application_type="web",
        site_name="Allrecipes",
        site_url="https://www.allrecipes.com/",
        output_artifact="recipe_choice.json",
        submission_profile="recipe_choice",
    ),
    "web_openlibrary-book-choice": PlaygroundTaskEntry(
        application_type="web",
        site_name="Open Library",
        site_url="https://openlibrary.org/",
        output_artifact="book_choice.json",
        submission_profile="book_choice",
    ),
    # Chatbot
    "chat_meal-planning-nutrition": PlaygroundTaskEntry(application_type="chatbot"),
    "chat_openbb-corporate-action-honesty": PlaygroundTaskEntry(
        application_type="chatbot"
    ),
    "example-chat-api_support_chatbot": PlaygroundTaskEntry(
        application_type="chatbot"
    ),
    "example-chat-mcp_support_chatbot": PlaygroundTaskEntry(
        application_type="chatbot"
    ),
    # Survey (questionnaire metadata mapping still lives in survey_task_content)
    "example-survey_product-feedback": PlaygroundTaskEntry(application_type="survey"),
    "survey_product-attitudes": PlaygroundTaskEntry(application_type="survey"),
    "survey_claude-code-vscode-checkpoints": PlaygroundTaskEntry(application_type="survey"),
    "survey_robinhood-cortex-digests": PlaygroundTaskEntry(application_type="survey"),
    "survey_cvs-prescription-ai": PlaygroundTaskEntry(application_type="survey"),
    "survey_nike-air-max-dn": PlaygroundTaskEntry(application_type="survey"),
}


def get_playground_entry(folder_name: str) -> PlaygroundTaskEntry | None:
    return PLAYGROUND_TASK_INDEX.get(folder_name)


def default_os_app_backend(meta_type: str, entry: PlaygroundTaskEntry, os: str = "") -> str:
    if entry.os_app_backend:
        return entry.os_app_backend
    os_key = (os or "").strip().lower()
    if os_key == "macos":
        return "macos"
    if os_key == "ios":
        return "ios"
    if meta_type == "mobile":
        return "ios"
    return "docker"


def default_os_app_platform(meta_type: str, os_app_backend: str, os: str = "") -> str:
    os_key = (os or "").strip().lower()
    if os_key:
        return os_key
    if os_app_backend == "macos":
        return "macos"
    if os_app_backend == "ios":
        return "ios"
    if meta_type == "web":
        return "web"
    if meta_type == "mobile":
        return "ios"
    if meta_type == "desktop":
        return "linux"
    return "linux"


def default_environment_label(os_app_platform: str) -> str:
    if os_app_platform == "linux":
        return "Docker Xvfb · persona-computer-1"
    if os_app_platform == "macos":
        return "use.computer · persona-computer-1"
    if os_app_platform == "ios":
        return "use.computer iOS · persona-computer-1"
    if os_app_platform == "web":
        return "Docker web CUA · persona-computer-1"
    return "persona-computer-1"
