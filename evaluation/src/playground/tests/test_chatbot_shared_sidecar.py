"""Tests for shared Playground chatbot sidecar helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from playground.inprocess import chatbot_shared_sidecar as shared


def test_pick_primary_prefers_known_adapter_service() -> None:
    assert (
        shared.pick_primary_sidecar_service(
            ["openbb-mcp", "finance-chatbot"]
        )
        == "finance-chatbot"
    )


def test_shared_spec_for_meal_plan() -> None:
    spec = shared.shared_spec_for_service("meal-plan-api")
    assert spec is not None
    assert spec.application_id == "meal_planning_nutrition"
    assert spec.host_port == 8905


def test_ensure_shared_returns_none_for_unknown_services(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(shared, "start_shared_sidecar", lambda **kwargs: "http://x")
    assert (
        shared.ensure_shared_sidecar_for_services(
            compose_dir=tmp_path,
            service_names=["totally-unknown-service"],
        )
        is None
    )


def test_start_shared_reuses_ready_sidecar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):  # noqa: ANN001
        calls.append(list(command))

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return Result()

    monkeypatch.setattr(shared.subprocess, "run", fake_run)
    monkeypatch.setattr(shared, "probe_shared_sidecar", lambda spec, timeout=None: True)
    spec = shared.shared_spec_for_service("meal-plan-api")
    assert spec is not None
    url = shared.start_shared_sidecar(compose_dir=tmp_path, spec=spec)
    assert url == "http://127.0.0.1:8905"
    assert calls == []


def test_start_shared_compose_up_when_not_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []
    ready_after = {"n": 0}

    def fake_probe(spec, timeout=None):  # noqa: ANN001
        ready_after["n"] += 1
        return ready_after["n"] >= 2

    def fake_run(command, **kwargs):  # noqa: ANN001
        calls.append(list(command))

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return Result()

    monkeypatch.setattr(shared, "probe_shared_sidecar", fake_probe)
    monkeypatch.setattr(shared.subprocess, "run", fake_run)
    monkeypatch.setattr(shared.time, "sleep", lambda _s: None)
    spec = shared.shared_spec_for_service("finance-chatbot")
    assert spec is not None
    url = shared.start_shared_sidecar(compose_dir=tmp_path, spec=spec, force_build=True)
    assert url == "http://127.0.0.1:8901"
    assert calls
    assert "--project-name" in calls[0]
    assert "playground-finance-openbb" in calls[0]
    assert "--build" in calls[0]
