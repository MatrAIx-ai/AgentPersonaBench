"""Deterministic synthetic display names for bench persona records."""

from __future__ import annotations

import hashlib
from typing import Any

_REGION_POOLS: dict[str, list[tuple[str, str]]] = {
    "East Asia": [
        ("Mei Lin", "Tan"),
        ("Yuki", "Sato"),
        ("Wei", "Zhang"),
        ("Hana", "Kim"),
        ("Jun", "Park"),
        ("Li Wei", "Chen"),
        ("Aiko", "Nakamura"),
        ("Min", "Ho"),
    ],
    "Southeast Asia": [
        ("Anh", "Nguyen"),
        ("Rizal", "Putra"),
        ("Siti", "Rahman"),
        ("Kai", "Lim"),
        ("Mai", "Tran"),
        ("Arif", "Hassan"),
    ],
    "South Asia": [
        ("Arjun", "Mehta"),
        ("Priya", "Sharma"),
        ("Rohan", "Kapoor"),
        ("Anika", "Das"),
        ("Vikram", "Singh"),
        ("Nisha", "Iyer"),
    ],
    "Western Europe": [
        ("Sofia", "Andersson"),
        ("Luka", "Petrov"),
        ("Emma", "Dubois"),
        ("Marco", "Rossi"),
        ("Clara", "Müller"),
        ("Noah", "Bakker"),
    ],
    "Eastern Europe": [
        ("Mila", "Novak"),
        ("Ivan", "Kowalski"),
        ("Elena", "Popescu"),
        ("Tomas", "Horvat"),
        ("Anya", "Volkova"),
        ("Petra", "Jansen"),
    ],
    "North America": [
        ("Jordan", "Lee"),
        ("Maya", "Patel"),
        ("Ethan", "Brooks"),
        ("Sienna", "Carter"),
        ("Noah", "Williams"),
        ("Ava", "Martinez"),
    ],
    "Latin America": [
        ("Camila", "Rojas"),
        ("Diego", "Fernandez"),
        ("Lucia", "Santos"),
        ("Mateo", "Garcia"),
        ("Valentina", "Lopez"),
        ("Andres", "Mendoza"),
    ],
    "MENA": [
        ("Layla", "Haddad"),
        ("Omar", "Khalil"),
        ("Yasmin", "Farouk"),
        ("Karim", "Nasser"),
        ("Nadia", "Rahman"),
        ("Samir", "Aziz"),
    ],
    "Sub-Saharan Africa": [
        ("Amara", "Okafor"),
        ("Kwame", "Mensah"),
        ("Zola", "Ndlovu"),
        ("Amina", "Diallo"),
        ("Tendai", "Moyo"),
        ("Kofi", "Adeyemi"),
    ],
    "Oceania": [
        ("Harper", "Ngata"),
        ("Liam", "Murphy"),
        ("Isla", "Campbell"),
        ("Jack", "Mitchell"),
        ("Ruby", "Taylor"),
        ("Finn", "Walsh"),
    ],
}

_DEFAULT_POOL: list[tuple[str, str]] = [
    ("Jordan", "Lee"),
    ("Maya", "Patel"),
    ("Alex", "Rivera"),
    ("Sam", "Okafor"),
    ("Riley", "Chen"),
    ("Casey", "Brooks"),
    ("Quinn", "Santos"),
    ("Avery", "Kim"),
]


def _hash_index(seed: str, modulo: int) -> int:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) % max(modulo, 1)


def synthetic_display_name(
    persona_id: str,
    dimensions: dict[str, Any] | None = None,
    *,
    salt: str = "",
) -> str:
    """Return a stable human-readable name for a bench persona.

    First and last names are drawn independently (cross-product of the region
    pool) so cohorts of 10+ personas rarely collide; `salt` lets callers probe
    for an unused name deterministically.
    """
    pid = str(persona_id or "").strip()
    dims = dimensions if isinstance(dimensions, dict) else {}
    region = str(dims.get("region") or "").strip()
    pool = _REGION_POOLS.get(region) or _DEFAULT_POOL
    seed = f"{pid}:{region}" if not salt else f"{pid}:{region}:{salt}"
    first = pool[_hash_index(f"{seed}:f", len(pool))][0]
    last = pool[_hash_index(f"{seed}:l", len(pool))][1]
    return f"{first} {last}"


def assign_cohort_display_names(
    entries: list[tuple[str, dict[str, Any] | None]],
) -> dict[str, str]:
    """Deterministic display names, unique within one cohort."""
    used: set[str] = set()
    named: dict[str, str] = {}
    for persona_id, dimensions in entries:
        name = synthetic_display_name(persona_id, dimensions)
        probe = 0
        while name in used and probe < 64:
            probe += 1
            name = synthetic_display_name(persona_id, dimensions, salt=str(probe))
        used.add(name)
        named[str(persona_id)] = name
    return named
