from backend.service.task_persona_strategy_service import get_task_persona_strategy


def test_get_task_persona_strategy_reads_json(tmp_path) -> None:
    task_dir = tmp_path / "application" / "tasks" / "example-survey-demo"
    task_dir.mkdir(parents=True)
    (task_dir / "persona_strategy.json").write_text(
        """
        {
          "schemaVersion": "1.0",
          "sampling": {"mode": "random", "sampleSize": 4},
          "dimensionFilters": {"age_bracket": ["18-24"]}
        }
        """.strip(),
        encoding="utf-8",
    )

    strategy = get_task_persona_strategy(
        "application/tasks/example-survey-demo",
        repo_root=tmp_path,
    )
    assert strategy is not None
    assert strategy["sampling"]["mode"] == "random"
    assert strategy["sampling"]["sampleSize"] == 4


def test_get_task_persona_strategy_missing_file_returns_none(tmp_path) -> None:
    task_dir = tmp_path / "application" / "tasks" / "example-web-demo"
    task_dir.mkdir(parents=True)

    assert (
        get_task_persona_strategy("application/tasks/example-web-demo", repo_root=tmp_path)
        is None
    )
