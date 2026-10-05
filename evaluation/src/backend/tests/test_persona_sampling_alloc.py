"""Unit tests for Hamilton / proportional stratum allocation."""

from __future__ import annotations

from backend.service.persona_sampling_alloc import hamilton_allocate


def test_hamilton_allocate_sums_to_sample_size() -> None:
    quotas = hamilton_allocate({"a": 50, "b": 30, "c": 20}, 10)
    assert sum(quotas.values()) == 10
    assert quotas["a"] >= quotas["b"] >= quotas["c"]


def test_hamilton_allocate_respects_availability() -> None:
    quotas = hamilton_allocate({"tiny": 1, "big": 99}, 5)
    assert sum(quotas.values()) == 5
    assert quotas["tiny"] <= 1
    assert quotas["big"] <= 99
