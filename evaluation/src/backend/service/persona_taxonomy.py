"""Three-layer MatrAIx persona taxonomy helpers for Playground detail views.

Maps schema ``category`` strings → Layer-1 groups → Layer-2 subgroups
(see ``persona/schema/matraix_persona_taxonomy_3layer_1290.md`` / PR #221).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

# (group_id, group_label, [(subgroup_id, subgroup_label, [schema category keys])])
TAXONOMY_3LAYER: list[tuple[str, str, list[tuple[str, str, list[str]]]]] = [
    (
        "background",
        "Background",
        [
            (
                "demographics",
                "Demographics",
                [
                    "Demographic: Core",
                    "Demographic: Family",
                    "Demographic: Cultural",
                    "Demographic: Life Events",
                ],
            ),
            ("language", "Language", ["Linguistic: Language", "Linguistic: Communication"]),
            ("education", "Education", ["Learning: Academic", "Learning: Style"]),
            (
                "career",
                "Career",
                [
                    "Professional: Career",
                    "Professional: Industry",
                    "Developer: Professional Context",
                ],
            ),
        ],
    ),
    (
        "psychology",
        "Psychology",
        [
            (
                "personality",
                "Personality",
                [
                    "Personality: Character",
                    "Personality: Big Five",
                    "Personality: MBTI",
                    "Personality: Relationships",
                ],
            ),
            ("worldview", "Worldview", ["Values & Motivation", "Worldview: Beliefs"]),
            ("decision_making", "Decision-making", ["Risk & Decision"]),
        ],
    ),
    (
        "capability",
        "Capability",
        [
            ("domains", "Domains", ["Expertise: Domains"]),
            (
                "skills",
                "Skills",
                [
                    "Expertise: Skills",
                    "Skills: Tools",
                    "Skills: Programming",
                    "Developer: Code Maintenance",
                ],
            ),
        ],
    ),
    (
        "behavior",
        "Behavior & interaction",
        [
            (
                "personal_behavior",
                "Personal behavior",
                ["Behavior: Preferences", "Behavior: Habits", "Behavior: Time"],
            ),
            ("interaction_state", "Interaction state", ["State: Emotional"]),
            (
                "work_practices",
                "Work practices",
                [
                    "Behavior: Work",
                    "Developer: Open Source Behavior",
                    "Developer: Community Behavior",
                ],
            ),
            (
                "technology_use",
                "Technology use",
                [
                    "Developer: AI Adoption",
                    "Developer: AI Workflow Tasks",
                    "Developer: Agent Adoption",
                    "Developer: Technology Evaluation",
                ],
            ),
        ],
    ),
    (
        "lifestyle",
        "Lifestyle & health",
        [
            (
                "interests",
                "Interests",
                [
                    "Interests: Topics",
                    "Interests: Media",
                    "Interests: Hobbies",
                    "Interests: Sports",
                    "Interests: Food",
                ],
            ),
            ("culture", "Culture & daily life", ["Interests: Culture"]),
            (
                "health",
                "Health",
                ["Health: Physical", "Health: Fitness", "Health: Lifestyle"],
            ),
        ],
    ),
]

_CATEGORY_INDEX: dict[str, tuple[str, str, str, str]] = {}
for group_id, group_label, subgroups in TAXONOMY_3LAYER:
    for subgroup_id, subgroup_label, categories in subgroups:
        for category in categories:
            _CATEGORY_INDEX[category] = (group_id, group_label, subgroup_id, subgroup_label)


def resolve_schema_path(repo_root: Path) -> Path | None:
    candidates = [
        repo_root / "persona/datasets/matraix-persona-1m/release/persona_codes.schema.json",
        repo_root / "persona/schema/persona_codes.schema.json",
        repo_root / "persona/schema/dimensions.json",
    ]
    try:
        from backend.service.persona_1m_pool import resolve_1m_paths

        paths = resolve_1m_paths(repo_root)
        candidates.insert(0, paths.schema_path)
    except Exception:  # noqa: BLE001
        pass
    for path in candidates:
        if path.is_file():
            return path
    return None


@lru_cache(maxsize=4)
def _load_schema_columns(schema_path: str) -> list[dict[str, Any]]:
    path = Path(schema_path)
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return []
    columns = payload.get("columns")
    if isinstance(columns, list):
        return [column for column in columns if isinstance(column, dict) and column.get("id")]
    # ``dimensions.json`` uses the same field shape under ``dimensions``.
    dimensions = payload.get("dimensions")
    if isinstance(dimensions, list):
        return [row for row in dimensions if isinstance(row, dict) and row.get("id")]
    return []


def _load_field_meta(schema_path: str) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for column in _load_schema_columns(schema_path):
        field_id = str(column.get("id") or "").strip()
        if not field_id:
            continue
        out[field_id] = {
            "label": str(column.get("label") or field_id.replace("_", " ")).strip(),
            "category": str(column.get("category") or "").strip(),
        }
    return out


def _humanize(field_id: str) -> str:
    return field_id.replace("_", " ").strip() or field_id


def build_dimension_groups(
    dimensions: dict[str, Any],
    *,
    repo_root: Path | None = None,
    schema_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Nest filled dimensions under the official 3-layer taxonomy."""
    cleaned = {
        str(key): str(value)
        for key, value in dict(dimensions or {}).items()
        if value is not None and str(value).strip()
    }
    if not cleaned:
        return []

    resolved = schema_path or (resolve_schema_path(repo_root) if repo_root else None)
    meta = _load_field_meta(str(resolved)) if resolved is not None else {}

    # group_id -> subgroup_id -> items
    buckets: dict[str, dict[str, list[dict[str, str]]]] = {
        group_id: {subgroup_id: [] for subgroup_id, _, _ in subgroups}
        for group_id, _, subgroups in TAXONOMY_3LAYER
    }
    other_items: list[dict[str, str]] = []

    for field_id, value in cleaned.items():
        info = meta.get(field_id) or {}
        label = info.get("label") or _humanize(field_id)
        category = info.get("category") or ""
        item = {
            "id": field_id,
            "label": label,
            "value": value,
            "category": category,
        }
        mapped = _CATEGORY_INDEX.get(category)
        if mapped is None:
            other_items.append(item)
            continue
        group_id, _group_label, subgroup_id, _subgroup_label = mapped
        buckets[group_id][subgroup_id].append(item)

    groups: list[dict[str, Any]] = []
    for group_id, group_label, subgroups in TAXONOMY_3LAYER:
        built_subgroups: list[dict[str, Any]] = []
        for subgroup_id, subgroup_label, _cats in subgroups:
            items = buckets[group_id][subgroup_id]
            if not items:
                continue
            items.sort(key=lambda row: row["label"].lower())
            built_subgroups.append(
                {
                    "id": subgroup_id,
                    "label": subgroup_label,
                    "count": len(items),
                    "items": items,
                }
            )
        if not built_subgroups:
            continue
        groups.append(
            {
                "id": group_id,
                "label": group_label,
                "count": sum(int(sub["count"]) for sub in built_subgroups),
                "subgroups": built_subgroups,
            }
        )

    if other_items:
        other_items.sort(key=lambda row: row["label"].lower())
        groups.append(
            {
                "id": "other",
                "label": "Other",
                "count": len(other_items),
                "subgroups": [
                    {
                        "id": "uncategorized",
                        "label": "Uncategorized",
                        "count": len(other_items),
                        "items": other_items,
                    }
                ],
            }
        )
    return groups


def build_production_filter_categories(
    *,
    repo_root: Path | None = None,
    schema_path: Path | None = None,
    persona_sources: list[str] | None = None,
) -> dict[str, Any]:
    """Full 1290-dim filter catalog for MatrAIx Persona 1M (3-layer taxonomy)."""
    resolved = schema_path or (resolve_schema_path(repo_root) if repo_root else None)
    if resolved is None:
        return {
            "schemaVersion": "1.0",
            "personaSources": list(persona_sources or []),
            "devProfile": {"dimensionCount": 0, "groups": []},
        }

    columns = _load_schema_columns(str(resolved))
    by_category: dict[str, list[dict[str, Any]]] = {}
    for column in columns:
        field_id = str(column.get("id") or "").strip()
        if not field_id:
            continue
        category = str(column.get("category") or "").strip()
        values = [str(v) for v in (column.get("values") or []) if str(v).strip()]
        dim = {
            "id": field_id,
            "label": str(column.get("label") or _humanize(field_id)).strip(),
            "values": values,
        }
        by_category.setdefault(category, []).append(dim)

    groups: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for group_id, group_label, subgroups in TAXONOMY_3LAYER:
        built_subgroups: list[dict[str, Any]] = []
        group_dim_ids: list[str] = []
        group_dims: list[dict[str, Any]] = []
        for subgroup_id, subgroup_label, categories in subgroups:
            dims: list[dict[str, Any]] = []
            for category in categories:
                dims.extend(by_category.get(category) or [])
            if not dims:
                continue
            # Stable unique by id within subgroup.
            unique: list[dict[str, Any]] = []
            local_seen: set[str] = set()
            for dim in dims:
                if dim["id"] in local_seen:
                    continue
                local_seen.add(dim["id"])
                unique.append(dim)
            unique.sort(key=lambda row: str(row.get("label") or row["id"]).lower())
            dim_ids = [str(dim["id"]) for dim in unique]
            for dim_id in dim_ids:
                seen_ids.add(dim_id)
            group_dim_ids.extend(dim_ids)
            group_dims.extend(unique)
            built_subgroups.append(
                {
                    "id": subgroup_id,
                    "label": subgroup_label,
                    "dimensionIds": dim_ids,
                    "dimensions": unique,
                }
            )
        if not built_subgroups:
            continue
        groups.append(
            {
                "id": group_id,
                "label": group_label,
                "dimensionIds": group_dim_ids,
                "dimensions": group_dims,
                "subgroups": built_subgroups,
            }
        )

    other_dims: list[dict[str, Any]] = []
    for column in columns:
        field_id = str(column.get("id") or "").strip()
        if not field_id or field_id in seen_ids:
            continue
        other_dims.append(
            {
                "id": field_id,
                "label": str(column.get("label") or _humanize(field_id)).strip(),
                "values": [str(v) for v in (column.get("values") or []) if str(v).strip()],
            }
        )
    if other_dims:
        other_dims.sort(key=lambda row: str(row.get("label") or row["id"]).lower())
        other_ids = [str(dim["id"]) for dim in other_dims]
        groups.append(
            {
                "id": "other",
                "label": "Other",
                "dimensionIds": other_ids,
                "dimensions": other_dims,
                "subgroups": [
                    {
                        "id": "uncategorized",
                        "label": "Uncategorized",
                        "dimensionIds": other_ids,
                        "dimensions": other_dims,
                    }
                ],
            }
        )

    return {
        "schemaVersion": "1.0",
        "personaSources": list(persona_sources or []),
        "devProfile": {
            "dimensionCount": len(columns),
            "groups": groups,
        },
    }
