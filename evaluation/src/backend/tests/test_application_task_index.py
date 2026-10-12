from backend.service.application_task_index import (
    clear_application_task_index_cache,
    discover_application_task_records,
    tasks_dir_signature,
)


def test_tasks_dir_signature_changes_when_task_toml_changes(tmp_path):
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    task_dir = tasks_dir / "survey_example"
    task_dir.mkdir()
    toml_path = task_dir / "task.toml"
    toml_path.write_text('[metadata]\ntype = "survey"\n', encoding="utf-8")

    first = tasks_dir_signature(tasks_dir)
    toml_path.write_text('[metadata]\ntype = "survey"\ndomain = "finance"\n', encoding="utf-8")
    second = tasks_dir_signature(tasks_dir)

    assert first != second


def test_discover_application_task_records_uses_manifest_cache(tmp_path):
    clear_application_task_index_cache()
    tasks_dir = tmp_path / "tasks"
    task_dir = tasks_dir / "survey_demo"
    input_dir = task_dir / "input"
    input_dir.mkdir(parents=True)
    (task_dir / "task.toml").write_text(
        "\n".join(
            [
                "[task]",
                'name = "application/survey-demo"',
                "[metadata]",
                'type = "survey"',
                'domain = "finance"',
            ]
        ),
        encoding="utf-8",
    )
    (task_dir / "instruction.md").write_text("# Demo Survey\n\nShort demo.", encoding="utf-8")
    (input_dir / "questionnaire.yaml").write_text(
        "id: demo_v1\ntitle: Demo\nquestions:\n  - id: q0\n    type: single\n",
        encoding="utf-8",
    )

    first = discover_application_task_records(application_type="survey", tasks_dir=tasks_dir)
    second = discover_application_task_records(application_type="survey", tasks_dir=tasks_dir)

    assert len(first) == 1
    assert first[0].folder_name == "survey_demo"
    assert second[0].task_path == first[0].task_path

    manifest = tmp_path / "cache" / "playground" / "task-index.json"
    assert not manifest.exists()

    clear_application_task_index_cache()
