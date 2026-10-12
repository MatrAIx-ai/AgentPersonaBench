"""Persona display helpers shared by Harbor debrief mappers and eval services."""

from __future__ import annotations

from typing import Any, Dict


def friendly_persona_name(persona: Any) -> str:
    """A recognizable display name for a persona.

    Datasets like Nemotron label personas ``"Source · id"``; the Catalog instead
    shows the occupation from the structured context. Mirror that here so a run's
    persona reads as e.g. "Financial Manager" rather than "Nemotron · 01B0D4D4".
    Falls back to the raw name (then source) when no occupation is present.
    """
    if isinstance(persona, dict):
        name = str(persona.get("name") or "")
        context = str(persona.get("context") or "")
        source = str(persona.get("source") or "")
    else:
        name = str(getattr(persona, "name", "") or "")
        context = str(getattr(persona, "context", "") or "")
        source = str(getattr(persona, "source", "") or "")
    for line in context.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("occupation:"):
            occupation = stripped.split(":", 1)[1].strip()
            if occupation:
                return occupation
    return name or source or "Persona"


def persona_summary(persona: Any) -> Dict[str, Any]:
    """Minimal persona view for debrief payloads."""
    return {
        "id": getattr(persona, "id", None) if not isinstance(persona, dict) else persona.get("id"),
        "name": friendly_persona_name(persona),
        "source": getattr(persona, "source", None) if not isinstance(persona, dict) else persona.get("source"),
        "context": getattr(persona, "context", None) if not isinstance(persona, dict) else persona.get("context"),
    }
