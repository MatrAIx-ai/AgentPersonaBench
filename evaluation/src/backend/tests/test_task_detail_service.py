"""Tests for task detail loading."""

from __future__ import annotations

from backend.service.task_detail_service import get_task_detail


def test_get_task_detail_reads_instruction_markdown(tmp_path):
    task_dir = tmp_path / "application" / "tasks" / "example-chat-api_demo"
    task_dir.mkdir(parents=True)
    (task_dir / "task.toml").write_text(
        "[metadata]\ntype = \"chat\"\n[task]\nname = \"demo/chat\"\n",
        encoding="utf-8",
    )
    (task_dir / "instruction.md").write_text(
        "# Demo Chat Task\n\nTalk to the sidecar naturally.\n\n## Steps\n\n1. Say hi.\n",
        encoding="utf-8",
    )
    detail = get_task_detail("application/tasks/example-chat-api_demo", repo_root=tmp_path)
    # Display title comes from ``[task].name`` (``demo/chat`` → ``Chat``), not instruction H1.
    assert detail["title"] == "Chat"
    assert "Talk to the sidecar" in detail["description"]
    assert "Say hi" in detail["profileMarkdown"]
    assert detail["metaType"] == "chatbot"


def test_get_task_detail_reads_split_survey_content_bundle(tmp_path):
    task_dir = tmp_path / "application" / "tasks" / "example-survey-demo"
    env_dir = tmp_path / "environment" / "task-environments" / "application" / "example-survey-demo" / "content"
    task_dir.mkdir(parents=True)
    env_dir.mkdir(parents=True)
    (task_dir / "task.toml").write_text(
        "\n".join(
            [
                "[metadata]",
                'type = "survey"',
                "[task]",
                'name = "demo/survey"',
                "[environment]",
                'definition = "application/example-survey-demo"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (task_dir / "instruction.md").write_text(
        "# Demo Structured Survey\n\nAnswer in character.\n",
        encoding="utf-8",
    )
    (env_dir / "context.md").write_text("This is the task context.", encoding="utf-8")
    (env_dir / "output_schema.md").write_text("Write strict JSON to `/app/output/survey_result.json`.", encoding="utf-8")
    (env_dir / "questionnaire.yaml").write_text(
        "\n".join(
            [
                'schemaVersion: "1.0"',
                "id: survey_demo_v1",
                "title: Demo Structured Survey",
                "questions:",
                "  - id: q1",
                "    prompt: Pick one option.",
                "    type: single_choice",
                "    construct: demo_construct",
                "    options:",
                "      - id: alpha",
                "        label: Alpha option",
                "      - id: beta",
                "        label: Beta option",
                "",
            ]
        ),
        encoding="utf-8",
    )

    detail = get_task_detail("application/tasks/example-survey-demo", repo_root=tmp_path)

    assert detail["metaType"] == "survey"
    assert detail["title"] == "Survey"
    assert detail["instructionMarkdown"] == "# Demo Structured Survey\n\nAnswer in character."
    assert detail["contextMarkdown"] == "This is the task context."
    assert "survey_result.json" in detail["outputSchemaMarkdown"]
    assert "Questionnaire" in detail["profileMarkdown"]
    assert "Answer envelope" in detail["profileMarkdown"]
    assert detail["questionnaire"]["questions"][0]["options"] == ["alpha", "beta"]
    assert detail["questionnaire"]["questions"][0]["optionDetails"][0]["label"] == "Alpha option"


def test_get_task_detail_reads_chat_self_report_schema(tmp_path):
    task_dir = tmp_path / "application" / "tasks" / "example-chat-demo"
    input_dir = task_dir / "input"
    task_dir.mkdir(parents=True)
    input_dir.mkdir(parents=True)
    (task_dir / "task.toml").write_text(
        "\n".join(
            [
                "[metadata]",
                'type = "chat"',
                "[task]",
                'name = "demo/chat"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (task_dir / "instruction.md").write_text(
        "# Demo Chat Task\n\nHave a natural support conversation.\n",
        encoding="utf-8",
    )
    (input_dir / "context.md").write_text("Order #4521 is late.", encoding="utf-8")
    (input_dir / "self_report_schema.yaml").write_text(
        "\n".join(
            [
                "artifactName: user_feedback.json",
                "fields:",
                "  - key: satisfaction",
                "    prompt: How satisfied were you?",
                "    kind: integer",
                "    minimum: 1",
                "    maximum: 5",
                "",
            ]
        ),
        encoding="utf-8",
    )

    detail = get_task_detail("application/tasks/example-chat-demo", repo_root=tmp_path)

    assert detail["metaType"] == "chatbot"
    assert detail["instructionMarkdown"] == "# Demo Chat Task\n\nHave a natural support conversation."
    assert detail["contextMarkdown"] == "Order #4521 is late."
    assert detail["outputSchemaMarkdown"] == ""
    assert "user_feedback.json" in detail["selfReportMarkdown"]
    assert "satisfaction" in detail["selfReportMarkdown"]
    assert "eval_artifacts.md" not in detail["selfReportMarkdown"]
    assert "Persona self-report" in detail["profileMarkdown"]
    assert detail["questionnaire"] is None


def test_get_task_detail_prefers_task_root_instruction_and_task_input_supplements(tmp_path):
    task_dir = tmp_path / "application" / "tasks" / "survey-preferred-input"
    input_dir = task_dir / "input"
    env_dir = (
        tmp_path
        / "environment"
        / "task-environments"
        / "application"
        / "shared-survey-env"
        / "content"
    )
    input_dir.mkdir(parents=True)
    env_dir.mkdir(parents=True)
    (task_dir / "task.toml").write_text(
        "\n".join(
            [
                "[metadata]",
                'type = "survey"',
                "[task]",
                'name = "demo/preferred-input"',
                "[environment]",
                'definition = "application/shared-survey-env"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (task_dir / "instruction.md").write_text(
        "# Preferred Input Survey\n\nRead task-root instruction.\n",
        encoding="utf-8",
    )
    (input_dir / "context.md").write_text("Task-local context.", encoding="utf-8")
    (input_dir / "output_schema.md").write_text(
        "Task-local schema to `/app/output/survey_result.json`.",
        encoding="utf-8",
    )
    (input_dir / "questionnaire.yaml").write_text(
        "\n".join(
            [
                'schemaVersion: "1.0"',
                "id: preferred_input_v1",
                "title: Preferred Input Survey",
                "questions:",
                "  - id: q1",
                "    prompt: Task local question",
                "    type: free_text",
                "    construct: open_feedback",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (env_dir / "instruction.md").write_text("Shared env instruction.", encoding="utf-8")
    (env_dir / "context.md").write_text("Shared env context.", encoding="utf-8")
    (env_dir / "output_schema.md").write_text("Shared env schema.", encoding="utf-8")

    detail = get_task_detail("application/tasks/survey-preferred-input", repo_root=tmp_path)

    assert detail["title"] == "Preferred Input"
    assert detail["instructionMarkdown"] == "# Preferred Input Survey\n\nRead task-root instruction."
    assert detail["contextMarkdown"] == "Task-local context."
    assert detail["outputSchemaMarkdown"] == "Task-local schema to `/app/output/survey_result.json`."
    assert detail["questionnaire"]["id"] == "preferred_input_v1"


def test_get_task_detail_ignores_shared_environment_content_without_task_input(tmp_path):
    task_dir = tmp_path / "application" / "tasks" / "chat-shared-env"
    env_dir = (
        tmp_path
        / "environment"
        / "task-environments"
        / "application"
        / "shared-chat-demo"
        / "content"
    )
    task_dir.mkdir(parents=True)
    env_dir.mkdir(parents=True)
    (task_dir / "task.toml").write_text(
        "\n".join(
            [
                "[metadata]",
                'type = "chat"',
                "[task]",
                'name = "demo/chat-shared"',
                "[environment]",
                'definition = "application/shared-chat-demo"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (task_dir / "instruction.md").write_text(
        "# Shared Chat Task\n\nTask-root instruction only.\n",
        encoding="utf-8",
    )
    (env_dir / "instruction.md").write_text("Shared env instruction.", encoding="utf-8")
    (env_dir / "context.md").write_text("Shared env context.", encoding="utf-8")
    (env_dir / "output_schema.md").write_text("Shared env schema.", encoding="utf-8")

    detail = get_task_detail("application/tasks/chat-shared-env", repo_root=tmp_path)

    assert detail["instructionMarkdown"] == "# Shared Chat Task\n\nTask-root instruction only."
    assert detail["contextMarkdown"] == ""
    assert detail["outputSchemaMarkdown"] == ""
    assert detail["selfReportMarkdown"] == ""


def test_get_task_detail_excludes_readme_from_profile_markdown(tmp_path):
    task_dir = tmp_path / "application" / "tasks" / "example-web-readme"
    task_dir.mkdir(parents=True)
    (task_dir / "task.toml").write_text(
        '[metadata]\ntype = "web"\n[task]\nname = "example/web-readme"\n',
        encoding="utf-8",
    )
    (task_dir / "instruction.md").write_text(
        "# Web Task\n\nBrowse the site and choose one option.\n",
        encoding="utf-8",
    )
    (task_dir / "README.md").write_text(
        "# Dev README\n\nHarbor agent setup notes for maintainers.\n",
        encoding="utf-8",
    )

    detail = get_task_detail("application/tasks/example-web-readme", repo_root=tmp_path)

    assert "Harbor agent setup notes" not in detail["profileMarkdown"]
    assert detail["instructionMarkdown"].startswith("# Web Task")
    assert detail["extraDocs"][0]["name"] == "README.md"
