"""Persona rendering + injection — the evaluation framework's persona pipeline.

Every task **embeds its own** persona: a self-contained ``persona.yaml`` in the
task directory, sampled from the real MatrAIx Persona 1M dataset to carry the
attribute value under test (plus a coherent surrounding profile). The file is
self-describing — each dimension already holds ``value`` + ``label`` +
``category`` — so rendering needs NO external schema (no dimensions.json):

    persona.yaml
      attributes:
        att_veganism:   {value: Enthusiast, label: "Attitude: Veganism", category: "Worldview: Beliefs"}
        lstyle_diet_type: {value: Vegan,     label: "Diet type",          category: "Health: Lifestyle"}
        ...

Usage from a solver — pass the task directory; the renderer finds persona.yaml:

    from evaluation.src.persona import persona_system_prompt
    sys = persona_system_prompt(task_dir, role="a user")

Rendering groups the attributes into taxonomy sections (by ``category``), skips
null/placeholder values, and wraps the result as a role-play system prompt —
identical wording across all tasks, no per-task prompt authoring.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

import yaml

# Soft budget for the persona block. Default unlimited — full profile is always
# kept so task-instruction append never forces persona truncation. Override with
# MATRAIX_PERSONA_PROFILE_MAX_CHARS only for emergency local debugging.
DEFAULT_PROFILE_MAX_CHARS: int | None = None

_NULLISH = frozenset(
    {
        "", "none", "n/a", "na", "null", "undefined", "none notable",
        "not applicable", "prefer not to say", "no coding activity",
        "not a developer", "no interest", "unknown",
    }
)

# Ordered sections — earlier = higher priority when soft-truncating. Each entry:
# (heading, category matchers). A matcher matches if category == it, or
# category.startswith(it) when the matcher ends with ":".
_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Identity", ("Demographic: Core", "Demographic: Cultural",
                  "Demographic: Family", "Demographic: Life Events")),
    ("Career & education", ("Professional: Career", "Professional: Industry",
                            "Learning: Academic", "Learning: Style", "Developer:")),
    ("Language & communication", ("Linguistic: Language", "Linguistic: Communication")),
    ("Personality & values", ("Personality: Big Five", "Personality: Character",
                              "Personality: MBTI", "Personality: Relationships",
                              "Values & Motivation", "Risk & Decision")),
    ("Current interaction state", ("State: Emotional", "Behavior: Time", "Behavior: Work")),
    ("Worldview", ("Worldview: Beliefs",)),
    ("Interests", ("Interests: Topics", "Interests: Hobbies", "Interests: Media",
                   "Interests: Culture", "Interests: Sports", "Interests: Food")),
    ("Skills & expertise", ("Expertise: Domains", "Expertise: Skills",
                            "Skills: Tools", "Skills: Programming")),
    ("Lifestyle & health", ("Health: Physical", "Health: Fitness", "Health: Lifestyle",
                            "Behavior: Preferences", "Behavior: Habits")),
)


# --------------------------------------------------------------------------- #
# Load
# --------------------------------------------------------------------------- #
def load_persona(source: str | os.PathLike) -> dict:
    """Load a task's embedded persona.yaml.

    `source` is a task directory (containing persona.yaml) or a direct path to a
    persona.yaml file.
    """
    p = Path(source)
    path = p / "persona.yaml" if p.is_dir() else p
    if not path.is_file():
        raise FileNotFoundError(f"no persona.yaml at {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_pinned_values(source: str | os.PathLike) -> dict[str, str]:
    """Return dimension values explicitly tested by a task's checks.

    A string such as ``"None"`` can be a valid categorical value even though
    it is normally suppressed as a placeholder.  Task checks disambiguate that
    case.  Direct persona paths remain supported by looking beside the file.
    """
    p = Path(source)
    task_path = (p if p.is_dir() else p.parent) / "task.toml"
    if not task_path.is_file():
        return {}
    task = tomllib.loads(task_path.read_text(encoding="utf-8"))
    checks = task.get("checks") or []
    if not isinstance(checks, list):
        return {}
    pinned: dict[str, str] = {}
    for check in checks:
        if not isinstance(check, dict):
            continue
        dimension_id = str(check.get("dimension_id") or "").strip()
        if not dimension_id or "value" not in check:
            continue
        value = check["value"]
        pinned[dimension_id] = "None" if value is None else str(value).strip()
    return pinned


# --------------------------------------------------------------------------- #
# Render
# --------------------------------------------------------------------------- #
def _keepable(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        text = ", ".join(str(v).strip() for v in value if str(v).strip())
    else:
        text = str(value).strip()
    if not text or text.lower() in _NULLISH:
        return None
    return text


def _section_for(category: str) -> str:
    for heading, matchers in _SECTIONS:
        for m in matchers:
            if m.endswith(":"):
                if category.startswith(m):
                    return heading
            elif category == m or category.startswith(f"{m}:"):
                return heading
    return "Other attributes"


def _resolve_max_chars(max_chars: int | None) -> int | None:
    if max_chars is not None:
        return None if max_chars <= 0 else max_chars
    raw = os.environ.get("MATRAIX_PERSONA_PROFILE_MAX_CHARS", "").strip()
    if raw:
        if raw.lower() in {"0", "none", "unlimited", "-1"}:
            return None
        try:
            v = int(raw)
        except ValueError:
            return DEFAULT_PROFILE_MAX_CHARS
        return None if v <= 0 else v
    return DEFAULT_PROFILE_MAX_CHARS


def build_dimension_narrative(
    persona: dict,
    *,
    max_chars: int | None = None,
    pinned_values: dict[str, str] | None = None,
) -> list[str]:
    """Group a self-contained persona's attributes into markdown section blocks."""
    attrs = persona.get("attributes") or {}
    pinned_values = pinned_values or {}
    # section -> [(label, value)]
    grouped: dict[str, list[tuple[str, str]]] = {}
    for dim_id, spec in attrs.items():
        if isinstance(spec, dict):
            raw_value = spec.get("value")
            label = str(spec.get("label") or dim_id.replace("_", " ")).strip()
            category = str(spec.get("category") or "")
        else:  # tolerate a bare value with no metadata
            raw_value = spec
            label = dim_id.replace("_", " ")
            category = ""
        value = pinned_values.get(dim_id) if dim_id in pinned_values else _keepable(raw_value)
        if value is None:
            continue
        grouped.setdefault(_section_for(category), []).append((label, value))

    order = [h for h, _ in _SECTIONS] + ["Other attributes"]
    budget = _resolve_max_chars(max_chars)
    rendered: list[str] = []
    omitted = 0
    used = 0
    for heading in order:
        items = grouped.get(heading)
        if not items:
            continue
        if budget is not None:
            remaining = budget - used - 80
            if remaining <= 0:
                omitted += len(items)
                continue
            fitted: list[tuple[str, str]] = []
            probe = len(f"### {heading}\n")
            for i, (label, value) in enumerate(items):
                line = len(f"- {label}: {value}\n")
                if probe + line > remaining:
                    omitted += len(items) - i
                    break
                fitted.append((label, value))
                probe += line
            if not fitted:
                omitted += len(items)
                continue
            items = fitted
        lines = [f"### {heading}"] + [f"- {label}: {value}" for label, value in items]
        block = "\n".join(lines)
        rendered.append(block)
        used += len(block) + 2

    if omitted:
        rendered.append(f"_…and {omitted} more attributes omitted to fit the context budget._")
    return rendered


def persona_system_prompt(source: str | os.PathLike, role: str = "a person") -> str:
    """Full persona (from the task's embedded persona.yaml) as a role-play prompt."""
    persona = load_persona(source)
    pinned_values = _load_pinned_values(source)
    profile = "\n\n".join(build_dimension_narrative(persona, pinned_values=pinned_values))
    return (
        f"You are role-playing {role} with the following profile. Stay fully in "
        f"character: let these traits shape your choices and language naturally, "
        f"the way a real person with this profile would behave. Do not announce "
        f"that you are role-playing.\n\n"
        f"# Your profile\n\n{profile}"
    )


def write_persona_prompt_file(source: str | os.PathLike, dest_dir: str | os.PathLike,
                              role: str = "a user") -> str | None:
    """Render the task's persona into a role-play prompt and write it to a file in
    dest_dir, returning the path. This is the injection format the harbor CUA agent
    consumes via --extra-instruction-path (harbor's own loader can't read our v2.0
    `attributes:` personas). Returns None if the persona renders empty.

    Keeping this in the persona layer (not the runner) keeps persona handling in
    one place; the file is a transient handoff, so callers pass a temp dest_dir.
    """
    prompt = persona_system_prompt(source, role=role)
    if not prompt or not prompt.strip():
        return None
    import pathlib
    out = pathlib.Path(dest_dir) / "persona_prompt.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(prompt, encoding="utf-8")
    return str(out)


if __name__ == "__main__":
    import sys

    src = sys.argv[1] if len(sys.argv) > 1 else "."
    print(persona_system_prompt(src, role="a user"))
