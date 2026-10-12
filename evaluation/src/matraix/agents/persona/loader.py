"""Load persona YAML files for persona-backed agents."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PERSONA_DOMAIN_KEYS = (
    "dimensions",
    "demographics",
    "psychology",
    "communication",
    "preferences",
    "behavior",
)

SCHEMA_V0 = "v0"
SCHEMA_V1 = "v1"
SCHEMA_V2 = "v2"


@dataclass(frozen=True)
class Persona:
    """Persona profile for Playground agents.

    Supports schema v0 (flat fields) and v1 (nested domains — see docs/personas/).
    """

    persona_path: Path
    schema_version: str
    data: dict[str, Any]
    persona_id: str | None
    version: str | None
    display_name: str | None
    summary: str | None
    system_prompt: str | None

    @property
    def dimensions(self) -> dict[str, Any]:
        return _as_dict(self.data.get("dimensions"))

    @property
    def demographics(self) -> dict[str, Any]:
        return _as_dict(self.data.get("demographics"))

    @property
    def psychology(self) -> dict[str, Any]:
        return _as_dict(self.data.get("psychology"))

    @property
    def communication(self) -> dict[str, Any]:
        return _as_dict(self.data.get("communication"))

    @property
    def preferences(self) -> dict[str, Any]:
        return _as_dict(self.data.get("preferences"))

    @property
    def behavior(self) -> dict[str, Any]:
        return _as_dict(self.data.get("behavior"))

    def has_domains(self) -> bool:
        return any(self.data.get(key) for key in PERSONA_DOMAIN_KEYS)

    def has_dimensions_schema(self) -> bool:
        return bool(self.dimensions)

    def template_context(self, *, instruction: str | None = None) -> dict[str, Any]:
        """Full Jinja context: YAML tree plus normalized top-level aliases."""
        context: dict[str, Any] = dict(self.data)
        context.update(
            {
                "schema_version": self.schema_version,
                "persona_id": self.persona_id,
                "version": self.version,
                "display_name": self.display_name,
                "summary": self.summary,
                "system_prompt": self.system_prompt,
                "dimensions": self.dimensions,
                "demographics": self.demographics,
                "psychology": self.psychology,
                "communication": self.communication,
                "preferences": self.preferences,
                "behavior": self.behavior,
            }
        )
        if instruction is not None:
            context["instruction"] = instruction
        return context

    def to_meta(self, agent_name: str) -> dict[str, str | None]:
        return {
            "persona_path": str(self.persona_path),
            "schema_version": self.schema_version,
            "persona_id": self.persona_id,
            "version": self.version,
            "display_name": self.display_name,
            "summary": self.summary,
            "agent": agent_name,
        }


def resolve_persona_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    resolved = candidate.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Persona file not found: {path}")
    return resolved


def load_persona(path: str | Path) -> Persona:
    resolved = resolve_persona_path(path)
    raw: Any = yaml.safe_load(resolved.read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"Persona YAML must be a mapping: {resolved}")

    persona_id = _optional_str(raw.get("persona_id"))
    version = _optional_str(raw.get("version"))
    display_name = _optional_str(raw.get("display_name"))
    summary = _optional_str(raw.get("summary"))
    system_prompt = _optional_str(raw.get("system_prompt"))
    has_domains = any(raw.get(key) for key in PERSONA_DOMAIN_KEYS)
    has_dimensions = isinstance(raw.get("dimensions"), dict) and bool(raw["dimensions"])

    if not display_name and persona_id:
        display_name = f"persona-{persona_id}"

    if has_dimensions:
        schema_version = SCHEMA_V2
    elif has_domains or persona_id:
        schema_version = SCHEMA_V1
    else:
        schema_version = SCHEMA_V0

    if not system_prompt and not has_domains:
        parts = []
        if display_name:
            parts.append(f"You are {display_name}.")
        if summary:
            parts.append(summary.strip())
        system_prompt = " ".join(parts).strip() or None

    if not system_prompt and not has_domains:
        raise ValueError(
            f"Persona {resolved} must define dimensions (v2), domain blocks (v1), or "
            "system_prompt / display_name+summary (v0)"
        )

    return Persona(
        persona_path=resolved,
        schema_version=schema_version,
        data=raw,
        persona_id=persona_id,
        version=version,
        display_name=display_name,
        summary=summary,
        system_prompt=system_prompt,
    )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
