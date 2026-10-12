"""Canonical Playground application scenario types (metadata + routing)."""

from __future__ import annotations

# Scenario ids — not agent names.
CANONICAL_APPLICATION_TYPES = frozenset({"survey", "chatbot", "web", "os-app"})

_METADATA_TYPE_ALIASES: dict[str, str] = {
    "chat": "chatbot",
    "cua": "os-app",
    "appworld": "os-app",
    "os_app": "os-app",
    "desktop": "os-app",
    "mobile": "os-app",
}


def normalize_metadata_type(raw: str | None) -> str:
    """Map Harbor ``metadata.type`` and legacy values to a canonical scenario id."""
    if raw is None:
        return ""
    key = str(raw).strip().lower()
    if not key:
        return ""
    return _METADATA_TYPE_ALIASES.get(key, key)
