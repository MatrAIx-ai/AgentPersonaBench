"""End-to-end tests for the playground API (:mod:`backend.api.app`).

Drives the real ``create_app`` via the shared ``client`` fixture (the fake
``recbot`` backend + temp catalog/store from ``conftest``). The personas
endpoint reads the real :mod:`playground.persona` catalog (336 curated YAML
personas; PyYAML only, no RecAI / OpenAI). For the job endpoints the
playground *service* on the app state is swapped for a tiny fake so ``start`` /
``view`` are exercised without ever running OpenAI or RecAI.

Covers:

* ``GET /api/playground/personas`` → un-filtered catalog with ``q``/``limit`` search.
* ``GET /api/playground/goal-contexts`` → seeded goal-context registry.
* ``POST /api/playground`` → ``200 {"jobId": ...}`` (delegates to ``service.start``),
  passing ``goalContextId``.
* ``GET /api/playground/jobs/{id}`` → the ``PlaygroundProgress.to_view()`` shape;
  unknown id → ``404``.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import pytest

# Skip the whole module cleanly if FastAPI/pydantic are unavailable in the env.
pytest.importorskip("fastapi")
pytest.importorskip("pydantic")


class _FakePlaygroundService:
    """Stand-in for :class:`backend.service.playground_service.PlaygroundService`.

    Records ``start`` calls and serves a single canned ``view``. Never runs the
    engine. Persona is domain-free, so there is no domain/persona guard.
    """

    def __init__(self) -> None:
        self.started: list = []
        #: The ``engine`` each ``start`` call received (parallel to ``started``),
        #: so a test can assert the request's RecBot engine was forwarded.
        self.started_engines: list = []
        #: The Harbor persona model each ``start`` call received.
        self.started_persona_models: list = []
        self._view: Dict[str, Any] = {
            "jobId": "wt_fake123",
            "domain": "game",
            "personaId": "game-lapsed-coop",
            "personaName": "Marco",
            "sutDescription": "desc",
            "goalContextId": "scenario_default",
            "status": "running",
            "phase": "recommender_thinking",
            "turns": [
                {
                    "turnId": "1",
                    "userMessage": "u1",
                    "assistantMessage": "a1",
                    "recommendedItems": [{"itemId": "6574", "title": "X"}],
                }
            ],
            "questionnaire": None,
            "metricScores": None,
            "prompts": {
                "harborPrompt": "Harbor persona prompt",
                "taskPrompt": "Application task prompt",
            },
            "error": None,
        }

    def start(
        self,
        domain: str,
        persona_id: str,
        max_turns: int,
        goal_context_id: str = "scenario_default",
        *,
        now,
        engine: Optional[str] = None,
        persona_model: Optional[str] = None,
        application_id: str = "meal_planning_nutrition",
        application_context: Optional[str] = None,
    ) -> str:
        self.started.append((domain, persona_id, max_turns, goal_context_id))
        self.started_engines.append(engine)
        self.started_persona_models.append(persona_model)
        self.started_application = {
            "applicationId": application_id,
            "applicationContext": application_context,
        }
        return "wt_fake123"

    def view(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._view if job_id == "wt_fake123" else None

    def list_runs(self) -> list:
        return [
            {
                "id": "wt_run1",
                "createdAt": "2026-02-02T00:00:00Z",
                "domain": "movie",
                "personaName": "Marco",
                "source": "Nemotron",
                "goalContextId": "scenario_default",
                "overallRating": 8,
                "numTurns": 2,
            }
        ]

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        if run_id != "wt_run1":
            return None
        return {
            "id": "wt_run1",
            "createdAt": "2026-02-02T00:00:00Z",
            "config": {"domain": "movie", "goalContextId": "scenario_default"},
            "persona": {
                "id": "game-lapsed-coop",
                "name": "Marco",
                "source": "Nemotron",
            },
            "sutDescription": "desc",
            "transcript": [
                {
                    "turnIndex": 1,
                    "userMessage": "u1",
                    "assistantMessage": "a1",
                    "recommendedItems": [{"id": "6574", "title": "X"}],
                    "decision": "satisfied",
                }
            ],
            "recommendedItemIds": {"perTurn": [["6574"]], "final": ["6574"]},
            "questionnaire": {"overallRating": 8},
            "metricScores": {"numTurns": 1},
            "prompts": {
                "harborPrompt": "Harbor persona prompt",
                "taskPrompt": "Application task prompt",
            },
        }


@pytest.fixture()
def fake_playground(app):
    """Swap the app-state playground service for the recording fake.

    Returns the fake so a test can assert what ``start`` received.
    """
    fake = _FakePlaygroundService()
    app.state.services.playground = fake
    return fake


# --------------------------------------------------------------------------- #
# Personas (real playground.persona fixtures — no service involved)
# --------------------------------------------------------------------------- #
def test_playground_personas_unfiltered(client):
    resp = client.get("/api/playground/personas")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body["personas"], list) and body["personas"]
    ids = {p["id"] for p in body["personas"]}
    # The curated YAML catalog is surfaced, no domain filter.
    assert "Nemotron_01B0D4D4" in ids
    persona = next(p for p in body["personas"] if p["id"] == "Nemotron_01B0D4D4")
    assert persona["source"] == "Nemotron"
    assert set(persona.keys()) >= {"id", "name", "source", "blurb"}
    assert "domain" not in persona
    # Sources are curated datasets only; no synthetic fixtures remain.
    sources = {p["source"] for p in body["personas"]}
    assert sources and "synthetic" not in sources


def test_playground_personas_search_and_limit(client):
    # ``q`` filters the catalog (search semantics covered in test_persona.py)
    # and ``limit`` caps the page; a known curated id is among the hits.
    body = client.get(
        "/api/playground/personas", params={"q": "software", "limit": 5}
    ).json()
    assert 0 < len(body["personas"]) <= 5
    assert any(p["id"] == "Nemotron_01B0D4D4" for p in body["personas"])


def test_playground_persona_detail(client):
    """The detail endpoint returns one persona's full humanized context.

    The list ships only a short ``blurb``; the catalog's "full persona" view
    fetches this endpoint for the complete, multi-line, humanized profile.
    """
    resp = client.get("/api/playground/personas/Nemotron_01B0D4D4")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == "Nemotron_01B0D4D4"
    assert body["source"] == "Nemotron"
    assert set(body.keys()) >= {"id", "name", "source", "context"}
    # Full context: multi-line, humanized, far richer than the list blurb.
    assert "\n" in body["context"]
    assert "Financial Manager" in body["context"]
    listed = client.get("/api/playground/personas").json()["personas"]
    blurb = next(p for p in listed if p["id"] == "Nemotron_01B0D4D4")["blurb"]
    assert len(body["context"]) > len(blurb)


def test_playground_persona_detail_unknown_404(client):
    assert client.get("/api/playground/personas/nope-not-real").status_code == 404


# --------------------------------------------------------------------------- #
# Goal contexts
# --------------------------------------------------------------------------- #
def test_playground_goal_contexts(client):
    resp = client.get("/api/playground/goal-contexts")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    ids = {gc["id"] for gc in body["goalContexts"]}
    assert {"scenario_default"} <= ids
    assert "gradual_reveal" not in ids  # collapsed into the single realistic scenario
    gc = next(g for g in body["goalContexts"] if g["id"] == "scenario_default")
    assert set(gc.keys()) >= {"id", "label", "description"}


# --------------------------------------------------------------------------- #
# Start + poll (fake service)
# --------------------------------------------------------------------------- #
def test_start_playground_returns_job_id(client, fake_playground):
    resp = client.post(
        "/api/playground",
        json={"domain": "game", "personaId": "game-lapsed-coop", "maxTurns": 4},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"jobId": "wt_fake123"}
    assert fake_playground.started == [
        ("game", "game-lapsed-coop", 4, "scenario_default")
    ]


def test_start_playground_default_max_turns(client, fake_playground):
    resp = client.post(
        "/api/playground",
        json={"domain": "game", "personaId": "game-lapsed-coop"},
    )
    assert resp.status_code == 200, resp.text
    # maxTurns defaults to 8, goalContextId defaults to scenario_default.
    assert fake_playground.started == [
        ("game", "game-lapsed-coop", 8, "scenario_default")
    ]


def test_start_playground_passes_goal_context(client, fake_playground):
    # The route forwards goalContextId as-is (it does not validate against the
    # registry), so future scenario ids need no route change.
    resp = client.post(
        "/api/playground",
        json={
            "domain": "game",
            "personaId": "game-lapsed-coop",
            "goalContextId": "future_scenario",
        },
    )
    assert resp.status_code == 200, resp.text
    assert fake_playground.started == [
        ("game", "game-lapsed-coop", 8, "future_scenario")
    ]


def test_start_playground_forwards_engine(client, fake_playground):
    # The selected engine reaches the service as the RecBot base model, not just
    # the cosmetic UI knob.
    resp = client.post(
        "/api/playground",
        json={"domain": "game", "personaId": "game-lapsed-coop", "engine": "gpt-4o"},
    )
    assert resp.status_code == 200, resp.text
    assert fake_playground.started_engines == ["gpt-4o"]


def test_start_playground_forwards_persona_model(client, fake_playground):
    resp = client.post(
        "/api/playground",
        json={
            "domain": "game",
            "personaId": "game-lapsed-coop",
            "personaModel": "anthropic/claude-sonnet-4-6",
        },
    )
    assert resp.status_code == 200, resp.text
    assert fake_playground.started_persona_models == ["anthropic/claude-sonnet-4-6"]


def test_start_playground_forwards_application_selection(client, fake_playground):
    resp = client.post(
        "/api/playground",
        json={
            "applicationId": "finance_openbb",
            "applicationContext": "financial_research",
            "domain": "game",
            "personaId": "game-lapsed-coop",
        },
    )
    assert resp.status_code == 200, resp.text
    assert fake_playground.started_application == {
        "applicationId": "finance_openbb",
        "applicationContext": "financial_research",
    }


def test_start_finance_playground_does_not_require_domain(client, fake_playground):
    resp = client.post(
        "/api/playground",
        json={
            "applicationId": "finance_openbb",
            "applicationContext": "financial_research",
            "personaId": "game-lapsed-coop",
        },
    )

    assert resp.status_code == 200, resp.text
    assert fake_playground.started == [
        ("financial_research", "game-lapsed-coop", 8, "scenario_default")
    ]
    assert fake_playground.started_application == {
        "applicationId": "finance_openbb",
        "applicationContext": "financial_research",
    }


def test_start_support_playground_does_not_require_domain(client, fake_playground):
    resp = client.post(
        "/api/playground",
        json={
            "applicationId": "acme_support_api",
            "personaId": "game-lapsed-coop",
        },
    )

    assert resp.status_code == 200, resp.text
    assert fake_playground.started == [
        ("customer_support", "game-lapsed-coop", 8, "scenario_default")
    ]
    assert fake_playground.started_application == {
        "applicationId": "acme_support_api",
        "applicationContext": "customer_support",
    }


def test_start_playground_defaults_engine_when_omitted(client, fake_playground):
    # An omitted engine falls back to the canonical config default so existing
    # behavior is unchanged.
    from backend.service.config import ConfigManager

    resp = client.post(
        "/api/playground",
        json={"domain": "game", "personaId": "game-lapsed-coop"},
    )
    assert resp.status_code == 200, resp.text
    assert fake_playground.started_engines == [ConfigManager.DEFAULTS["engine"]]
    assert fake_playground.started_persona_models == ["anthropic/claude-haiku-4-5"]


def test_start_playground_any_persona_any_domain(client, fake_playground):
    # Persona is domain-free: a "game" persona may run a "movie" domain.
    resp = client.post(
        "/api/playground",
        json={"domain": "movie", "personaId": "game-lapsed-coop"},
    )
    assert resp.status_code == 200, resp.text
    assert fake_playground.started == [
        ("movie", "game-lapsed-coop", 8, "scenario_default")
    ]


def test_get_playground_job_view(client, fake_playground):
    resp = client.get("/api/playground/jobs/wt_fake123")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["jobId"] == "wt_fake123"
    assert body["status"] == "running"
    assert body["personaName"] == "Marco"
    assert body["sutDescription"] == "desc"
    assert body["goalContextId"] == "scenario_default"
    assert len(body["turns"]) == 1
    assert body["turns"][0]["recommendedItems"][0]["itemId"] == "6574"
    assert body["prompts"] == {
        "harborPrompt": "Harbor persona prompt",
        "taskPrompt": "Application task prompt",
    }


def test_get_playground_job_unknown_404(client, fake_playground):
    resp = client.get("/api/playground/jobs/wt_nope")
    assert resp.status_code == 404


# --------------------------------------------------------------------------- #
# Runs (list / get)
# --------------------------------------------------------------------------- #
def test_list_playground_runs(client, fake_playground):
    resp = client.get("/api/playground/runs")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body["runs"], list) and len(body["runs"]) == 1
    run = body["runs"][0]
    assert run["id"] == "wt_run1"
    assert run["domain"] == "movie"
    assert run["personaName"] == "Marco"
    assert run["source"] == "Nemotron"
    assert run["goalContextId"] == "scenario_default"
    assert run["overallRating"] == 8
    assert run["numTurns"] == 2


def test_get_playground_run(client, fake_playground):
    resp = client.get("/api/playground/runs/wt_run1")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == "wt_run1"
    assert body["persona"]["name"] == "Marco"
    assert body["questionnaire"]["overallRating"] == 8
    assert body["transcript"][0]["recommendedItems"][0]["id"] == "6574"
    assert body["recommendedItemIds"]["final"] == ["6574"]
    assert body["prompts"] == {
        "harborPrompt": "Harbor persona prompt",
        "taskPrompt": "Application task prompt",
    }


def test_get_playground_run_unknown_404(client, fake_playground):
    resp = client.get("/api/playground/runs/wt_nope")
    assert resp.status_code == 404


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def test_start_playground_bad_domain_422(client):
    resp = client.post(
        "/api/playground",
        json={"domain": "bogus", "personaId": "game-lapsed-coop"},
    )
    assert resp.status_code == 422


def test_start_playground_bad_max_turns_422(client):
    resp = client.post(
        "/api/playground",
        json={"domain": "game", "personaId": "game-lapsed-coop", "maxTurns": 0},
    )
    assert resp.status_code == 422
