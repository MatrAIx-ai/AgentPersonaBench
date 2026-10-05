from pathlib import Path

from playground.runner import run_playground
from playground.types import Persona, PlaygroundConfig


def _persona():
    return Persona(
        id="p",
        name="Marco",
        summary="s",
        preferences=[],
        dislikes=[],
        constraints=[],
        goal="g",
        communication_style="c",
    )


def test_runner_delegates_to_canonical_user_sim(monkeypatch):
    sentinel = object()
    captured = {}

    def fake_run(session, persona, sut_description, config, *, created_at, on_event, task_path, persona_yaml_path, repo_root):
        captured["session"] = session
        captured["persona"] = persona
        captured["sut_description"] = sut_description
        captured["config"] = config
        captured["created_at"] = created_at
        captured["task_path"] = task_path
        captured["persona_yaml_path"] = persona_yaml_path
        captured["repo_root"] = repo_root
        return sentinel

    monkeypatch.setattr("playground.user_sim.runner.run_playground", fake_run)
    config = PlaygroundConfig(domain="game", max_turns=3)
    session = object()
    persona = _persona()

    result = run_playground(
        session,
        persona,
        "desc",
        config,
        created_at="t",
        on_event=None,
        task_path="application/tasks/chat_meal-planning-nutrition",
        persona_yaml_path="persona.yaml",
        repo_root=Path("/tmp/demo-repo"),
    )

    assert result is sentinel
    assert captured == {
        "session": session,
        "persona": persona,
        "sut_description": "desc",
        "config": config,
        "created_at": "t",
        "task_path": "application/tasks/chat_meal-planning-nutrition",
        "persona_yaml_path": "persona.yaml",
        "repo_root": Path("/tmp/demo-repo"),
    }
