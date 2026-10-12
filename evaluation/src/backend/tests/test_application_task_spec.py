from __future__ import annotations

import json
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
TASKS_ROOT = REPO_ROOT / "application" / "tasks"
ENVIRONMENTS_ROOT = (
    REPO_ROOT / "evaluation" / "src" / "environment" / "task-environments" / "application"
)
TASK_SPEC_ROOT = REPO_ROOT / "application" / "task-spec"


def test_application_task_spec_manifest_groups_core_protocols() -> None:
    manifest = json.loads((TASK_SPEC_ROOT / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["schemaVersion"] == "application-task-spec-v1"
    assert set(manifest["applicationTypes"]) == {
        "survey",
        "chatbot",
        "web",
        "os-app",
    }
    assert manifest["applicationTypes"]["survey"]["canonicalTask"] == (
        "application/tasks/example-survey_product-feedback"
    )
    assert manifest["applicationTypes"]["chatbot"]["canonicalTask"] == (
        "application/tasks/example-chat-api_support_chatbot"
    )
    assert manifest["applicationTypes"]["web"]["canonicalTask"] == (
        "application/tasks/example-web-playwright_quote-choice"
    )
    assert manifest["applicationTypes"]["os-app"]["canonicalTask"] == (
        "application/tasks/example-computer-use-ios_photo-access-review"
    )


def test_application_task_spec_docs_exist_for_each_protocol() -> None:
    for dirname in ("survey", "chatbot", "web"):
        doc = TASK_SPEC_ROOT / dirname / "README.md"
        assert doc.is_file(), doc
        text = doc.read_text(encoding="utf-8")
        assert "Task instruction" in text
        assert "Interaction protocol" in text
        assert "Evaluation contract" in text


def test_application_tasks_do_not_embed_runtime_environments() -> None:
    embedded = sorted(path.relative_to(TASKS_ROOT) for path in TASKS_ROOT.glob("*/environment"))
    assert embedded == []


def test_canonical_survey_task_shape() -> None:
    task = TASKS_ROOT / "example-survey_product-feedback"
    raw = tomllib.loads((task / "task.toml").read_text(encoding="utf-8"))

    assert raw["task"]["name"] == "application/product-feedback"
    assert raw["metadata"]["type"] == "survey"
    assert raw["metadata"]["domain"] == "software"
    assert "/app/output" in raw["artifacts"]
    assert raw["environment"]["definition"] == "application/shared-survey-form"
    assert (task / "input" / "questionnaire.yaml").is_file()
    assert "test_state.py" in (
        task / "tests" / "test.sh"
    ).read_text(encoding="utf-8")


def test_survey_reference_tasks_use_shared_runtime_and_task_local_input() -> None:
    for folder in (
        "example-survey_product-feedback",
        "survey_annual-checkup-habits",
    ):
        task = TASKS_ROOT / folder
        raw = tomllib.loads((task / "task.toml").read_text(encoding="utf-8"))

        assert raw["metadata"]["type"] == "survey"
        assert raw["environment"]["definition"] == "application/shared-survey-form"
        assert (task / "instruction.md").is_file()
        assert (task / "input" / "context.md").is_file()
        assert (task / "input" / "questionnaire.yaml").is_file()
        assert not (task / "input" / "output_schema.md").exists()
        questionnaire = (task / "input" / "questionnaire.yaml").read_text(encoding="utf-8")
        # Defaults are false; tasks may omit the keys entirely.
        assert "output_schema" not in questionnaire


def test_canonical_chatbot_task_shape() -> None:
    task = TASKS_ROOT / "example-chat-api_support_chatbot"
    persona = ENVIRONMENTS_ROOT / "shared-chat-persona"
    sidecar = ENVIRONMENTS_ROOT / "chatbot-api-sidecar_acme-support-api"
    raw = tomllib.loads((task / "task.toml").read_text(encoding="utf-8"))

    assert raw["task"]["name"] == "application/api-support-chatbot"
    assert raw["metadata"]["type"] == "chatbot"
    assert raw["metadata"]["domain"] == "commerce-retail"
    assert raw["environment"]["definition"] == "application/shared-chat-persona"
    assert (
        raw["environment"]["local_compose"]
        == "application/chatbot-api-sidecar_acme-support-api"
    )
    assert "/app/output" in raw["artifacts"]
    assert (persona / "Dockerfile").is_file()
    assert (sidecar / "support-api" / "server.py").is_file()
    assert (task / "input" / "self_report_schema.yaml").is_file()
    assert not (task / "input" / "output_schema.md").exists()


def test_canonical_web_task_shape() -> None:
    task = TASKS_ROOT / "example-web-playwright_quote-choice"
    env = ENVIRONMENTS_ROOT / "shared-web-playwright"
    raw = tomllib.loads((task / "task.toml").read_text(encoding="utf-8"))

    assert raw["task"]["name"] == "application/playwright-quote-choice"
    assert raw["metadata"]["type"] == "web"
    assert raw["metadata"]["domain"] == "arts-culture"
    assert raw["environment"]["definition"] == "application/shared-web-playwright"
    assert "/app/output" in raw["artifacts"]
    assert (task / "input" / "self_report_schema.yaml").is_file()
    assert (task / "input" / "context.md").is_file()
    assert "quote_choice.json" in (task / "instruction.md").read_text(encoding="utf-8")
    dockerfile = (env / "Dockerfile").read_text(encoding="utf-8")
    assert "playwright" in dockerfile.lower()
    assert "python" in dockerfile.lower()


def test_shared_web_cli_environment_shape() -> None:
    env = ENVIRONMENTS_ROOT / "shared-web-cli"
    dockerfile = (env / "Dockerfile").read_text(encoding="utf-8")
    assert (env / "install-claude-code.sh").is_file()
    assert "playwright" in dockerfile.lower()
    assert "install-claude-code.sh" in dockerfile


def test_canonical_os_app_task_shape() -> None:
    task = TASKS_ROOT / "example-computer-use-ios_photo-access-review"
    raw = tomllib.loads((task / "task.toml").read_text(encoding="utf-8"))

    assert raw["metadata"]["type"] == "os-app"
    assert raw["environment"]["definition"] == "application/shared-os-app-mac-ios"
    assert (ENVIRONMENTS_ROOT / "shared-os-app-mac-ios").is_dir()
    assert (ENVIRONMENTS_ROOT / "shared-os-app-linux" / "Dockerfile").is_file()
    assert (task / "instruction.md").is_file()
    assert (task / "input" / "context.md").is_file()
    assert "input/context.md" in (task / "instruction.md").read_text(encoding="utf-8")
    assert "decision.json" in (task / "instruction.md").read_text(encoding="utf-8")
