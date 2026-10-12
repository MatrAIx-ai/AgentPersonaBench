"""Shared stratified allocation helpers (Hamilton / largest-remainder)."""

from __future__ import annotations

import random
from typing import Any


def hamilton_allocate(counts: dict[str, int], sample_size: int) -> dict[str, int]:
    """Largest-remainder allocation: quotas sum to ``sample_size``."""
    if sample_size < 1:
        raise ValueError("sample_size must be >= 1")
    positive = {key: count for key, count in counts.items() if count > 0}
    if not positive:
        raise ValueError("No non-empty strata for proportional allocation")
    total = sum(positive.values())
    if sample_size > total:
        raise ValueError(
            "sample_size={} exceeds matched pool size={}".format(sample_size, total)
        )
    raw = {key: sample_size * (count / total) for key, count in positive.items()}
    floors = {key: int(value) for key, value in raw.items()}
    assigned = sum(floors.values())
    remainders = sorted(
        ((raw[key] - floors[key], key) for key in floors),
        key=lambda item: (-item[0], item[1]),
    )
    quotas = dict(floors)
    for index in range(sample_size - assigned):
        quotas[remainders[index][1]] += 1
    surplus = 0
    for key, quota in list(quotas.items()):
        avail = positive[key]
        if quota > avail:
            surplus += quota - avail
            quotas[key] = avail
    if surplus:
        for _ in range(surplus):
            donors = sorted(
                (
                    (positive[k] - quotas[k], k)
                    for k in quotas
                    if positive[k] > quotas[k]
                ),
                key=lambda item: (-item[0], item[1]),
            )
            if not donors:
                break
            quotas[donors[0][1]] += 1
    return quotas


def sample_proportional_from_buckets(
    buckets: dict[Any, list[dict[str, Any]]],
    *,
    sample_size: int,
    seed: int,
) -> list[dict[str, Any]]:
    counts = {str(key): len(rows) for key, rows in buckets.items()}
    key_map = {str(key): key for key in buckets}
    quotas = hamilton_allocate(counts, sample_size)
    rng = random.Random(seed)
    chosen: list[dict[str, Any]] = []
    for key_str in sorted(quotas):
        take = quotas[key_str]
        if take <= 0:
            continue
        pool = list(buckets[key_map[key_str]])
        rng.shuffle(pool)
        chosen.extend(pool[:take])
    rng.shuffle(chosen)
    return chosen
