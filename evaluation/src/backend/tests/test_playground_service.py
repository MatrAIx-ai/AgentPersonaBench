import json
import time
from backend.service.playground_service import PlaygroundService
from playground.types import (
    Persona,
    Questionnaire,
    MetricScores,
    PlaygroundResult,
    PlaygroundTurn,
)


class FakeSession:
    def __init__(self):
        self.turns = []


def _persona():
    return Persona(
        id="game-x",
        name="Marco",
        summary="s",
        context="ctx",
        source="Nemotron",
        preferences=[],
        dislikes=[],
        constraints=[],
        goal="g",
        communication_style="c",
    )


def _fake_runner(session, persona, sut, config, simulator, *, created_at, on_event):
    # emit two turns then done, mutating the session like the real runner's session does
    for i in (1, 2):
        session.turns.append(
            {
                "turnId": str(i),
                "userMessage": "u%d" % i,
                "assistantMessage": "a%d" % i,
                "recommendedItems": [{"itemId": "6574", "title": "X"}]
                if i == 2
                else [],
            }
        )
        on_event({"type": "turn", "turn": session.turns[-1]})
    q = Questionnaire(4, "", 4, "", 8, "ok", True, "")
    res = PlaygroundResult(
        config=config,
        persona=persona,
        sut_description=sut,
        transcript=[
            PlaygroundTurn(2, "u2", "a2", [{"id": "6574", "title": "X"}], "satisfied")
        ],
        questionnaire=q,
        metric_scores=MetricScores(2, 2, 1),
        created_at=created_at,
    )
    on_event({"type": "done", "result": res.to_dict()})
    return res


def _service(record=None, runs_dir=None, configs=None):
    def simulator_factory(engine, gid, domain):
        if record is not None:
            record.append((engine, gid, domain))
        return object()

    return PlaygroundService(
        session_builder=lambda config: (
            (configs.append(config) if configs is not None else None) or FakeSession()
        ),
        get_persona=lambda pid: _persona(),
        sut_for=lambda d: "desc",
        simulator_factory=simulator_factory,
        runner=_fake_runner,
        runs_dir=runs_dir,
    )


def _wait_done(svc, job_id, timeout=2.0):
    end = time.time() + timeout
    while time.time() < end:
        v = svc.view(job_id)
        if v and v["status"] in ("done", "error"):
            return v
        time.sleep(0.01)
    return svc.view(job_id)


def test_start_runs_and_streams_turns_then_done(tmp_path):
    svc = _service(runs_dir=tmp_path)
    job_id = svc.start("game", "game-x", 6, now=lambda: "t")
    view = _wait_done(svc, job_id)
    assert view["status"] == "done"
    assert view["personaName"] == "Marco" and view["sutDescription"] == "desc"
    assert len(view["turns"]) == 2
    assert view["turns"][1]["recommendedItems"][0]["itemId"] == "6574"
    assert view["questionnaire"]["overallRating"] == 8
    assert view["metricScores"]["turnsToRecommendation"] == 2


def test_runner_return_populates_final_progress_without_done_event(tmp_path):
    def runner_without_done(
        session, persona, sut, config, simulator, *, created_at, on_event
    ):
        del simulator, on_event
        session.turns.append(
            {"turnId": "0", "userMessage": "u", "assistantMessage": "a"}
        )
        return PlaygroundResult(
            config=config,
            persona=persona,
            sut_description=sut,
            transcript=[],
            questionnaire=Questionnaire(3, "", 3, "", 6, "ok", True, ""),
            metric_scores=MetricScores(1, 1, 0),
            created_at=created_at,
        )

    svc = PlaygroundService(
        session_builder=lambda config: FakeSession(),
        get_persona=lambda pid: _persona(),
        sut_for=lambda d: "desc",
        simulator_factory=lambda e, g, d2: object(),
        runner=runner_without_done,
        runs_dir=tmp_path,
    )
    job_id = svc.start("game", "game-x", 6, now=lambda: "t")
    view = _wait_done(svc, job_id)
    assert view["status"] == "done"
    assert view["questionnaire"]["overallRating"] == 6
    assert view["metricScores"]["numTurns"] == 1


def test_prompt_event_and_result_prompts_reach_progress_and_persistence(tmp_path):
    class ResultWithPrompts:
        def __init__(self, config, persona, sut, created_at):
            self.config = config
            self.persona = persona
            self.sut = sut
            self.created_at = created_at

        def to_dict(self):
            return {
                "config": self.config.to_dict(),
                "persona": self.persona.to_dict(),
                "sutDescription": self.sut,
                "transcript": [],
                "recommendedItemIds": {"perTurn": [], "final": []},
                "questionnaire": {"overallRating": 7},
                "metricScores": {"numTurns": 0},
                "createdAt": self.created_at,
                "prompts": {
                    "harborPrompt": "Harbor persona prompt",
                    "taskPrompt": "Application task prompt",
                },
            }

    def runner_with_prompts(
        session, persona, sut, config, simulator, *, created_at, on_event
    ):
        del session, simulator
        on_event(
            {
                "type": "prompts",
                "prompts": {
                    "harborPrompt": "Harbor persona prompt",
                    "taskPrompt": "Application task prompt",
                },
            }
        )
        return ResultWithPrompts(config, persona, sut, created_at)

    svc = PlaygroundService(
        session_builder=lambda config: FakeSession(),
        get_persona=lambda pid: _persona(),
        sut_for=lambda d: "desc",
        simulator_factory=lambda e, g, d2: object(),
        runner=runner_with_prompts,
        runs_dir=tmp_path,
    )

    job_id = svc.start("game", "game-x", 6, now=lambda: "t")
    view = _wait_done(svc, job_id)

    assert view["status"] == "done"
    assert view["prompts"] == {
        "harborPrompt": "Harbor persona prompt",
        "taskPrompt": "Application task prompt",
    }
    stored = json.loads((tmp_path / "{}.json".format(job_id)).read_text())
    assert stored["prompts"] == view["prompts"]


def test_goal_context_id_defaults_and_reaches_factory(tmp_path):
    record = []
    svc = _service(record, runs_dir=tmp_path)
    job_id = svc.start("game", "game-x", 6, now=lambda: "t")
    view = _wait_done(svc, job_id)
    assert view["status"] == "done"
    assert view["goalContextId"] == "scenario_default"
    assert record == [("gpt-4o-mini", "scenario_default", "game")]


def test_goal_context_id_passes_through(tmp_path):
    record = []
    svc = _service(record, runs_dir=tmp_path)
    # Any id forwards through the service unchanged (the registry can grow later).
    job_id = svc.start("game", "game-x", 6, "future_scenario", now=lambda: "t")
    view = _wait_done(svc, job_id)
    assert view["status"] == "done"
    assert view["goalContextId"] == "future_scenario"
    assert record == [("gpt-4o-mini", "future_scenario", "game")]


def test_persona_model_reaches_config(tmp_path):
    configs = []
    svc = _service(runs_dir=tmp_path, configs=configs)
    job_id = svc.start(
        "game",
        "game-x",
        6,
        now=lambda: "t",
        persona_model="anthropic/claude-sonnet-4-6",
    )
    view = _wait_done(svc, job_id)
    assert view["status"] == "done"
    assert configs[0].persona_model == "anthropic/claude-sonnet-4-6"


def test_no_persona_domain_validation(tmp_path):
    # Persona is domain-free; any persona may run against any domain.
    svc = _service(runs_dir=tmp_path)
    job_id = svc.start("movie", "game-x", 6, now=lambda: "t")
    view = _wait_done(svc, job_id)
    assert view["status"] == "done"


def test_view_unknown_job_is_none():
    assert _service().view("nope") is None


def test_done_run_is_persisted_to_runs_dir(tmp_path):
    svc = _service(runs_dir=tmp_path)
    job_id = svc.start("game", "game-x", 6, now=lambda: "t")
    view = _wait_done(svc, job_id)
    assert view["status"] == "done"
    path = tmp_path / "{}.json".format(job_id)
    assert path.exists()
    stored = json.loads(path.read_text())
    # The stored artifact is the full result.to_dict() plus a top-level id.
    assert stored["id"] == job_id
    assert stored["questionnaire"]["overallRating"] == 8
    assert stored["persona"]["name"] == "Marco"
    assert stored["config"]["domain"] == "game"
    assert stored["createdAt"] == "t"
    assert "transcript" in stored and "recommendedItemIds" in stored


def test_list_runs_returns_newest_first_summaries(tmp_path):
    svc = _service(runs_dir=tmp_path)
    first = _wait_done(
        svc, svc.start("game", "game-x", 6, now=lambda: "2026-01-01T00:00:00Z")
    )
    second = _wait_done(
        svc, svc.start("movie", "game-x", 6, now=lambda: "2026-02-02T00:00:00Z")
    )
    assert first["status"] == "done" and second["status"] == "done"
    runs = svc.list_runs()
    assert len(runs) == 2
    # newest-first by createdAt
    assert runs[0]["createdAt"] == "2026-02-02T00:00:00Z"
    assert runs[1]["createdAt"] == "2026-01-01T00:00:00Z"
    summary = runs[0]
    assert set(summary.keys()) >= {
        "id",
        "createdAt",
        "domain",
        "personaName",
        "source",
        "goalContextId",
        "overallRating",
        "numTurns",
    }
    assert summary["domain"] == "movie"
    assert summary["personaName"] == "Marco"
    assert summary["source"] == "Nemotron"
    assert summary["goalContextId"] == "scenario_default"
    assert summary["overallRating"] == 8
    assert summary["numTurns"] == 2


def test_get_run_round_trips(tmp_path):
    svc = _service(runs_dir=tmp_path)
    job_id = svc.start("game", "game-x", 6, now=lambda: "t")
    _wait_done(svc, job_id)
    run = svc.get_run(job_id)
    assert run is not None
    assert run["id"] == job_id
    assert run["questionnaire"]["overallRating"] == 8
    assert svc.get_run("nope") is None


def test_get_run_injects_id_for_legacy_artifact(tmp_path):
    # CLI-written artifacts predate _persist_run's id injection (no top-level id);
    # get_run must still satisfy the PlaygroundResultView contract (id required).
    (tmp_path / "legacy-persona.json").write_text(
        json.dumps(
            {
                "config": {"domain": "game"},
                "questionnaire": {"overallRating": 7},
            }
        ),
        encoding="utf-8",
    )
    svc = _service(runs_dir=tmp_path)
    run = svc.get_run("legacy-persona")
    assert run is not None and run["id"] == "legacy-persona"


def test_no_persistence_without_runs_dir(tmp_path):
    # Default runs_dir is the canonical cache dir; tests inject one. With none
    # injected and no disk writes expected, list_runs is still callable.
    svc = _service(runs_dir=tmp_path)
    assert svc.list_runs() == []
    assert svc.get_run("nope") is None


def test_runner_exception_marks_error():
    def boom(*a, **k):
        raise RuntimeError("kaboom")

    svc = PlaygroundService(
        session_builder=lambda c: FakeSession(),
        get_persona=lambda p: _persona(),
        sut_for=lambda d: "desc",
        simulator_factory=lambda e, g, d2: object(),
        runner=boom,
    )
    job_id = svc.start("game", "game-x", 6, now=lambda: "t")
    view = _wait_done(svc, job_id)
    assert view["status"] == "error" and "kaboom" in view["error"]
