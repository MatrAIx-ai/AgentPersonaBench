from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from playground.paths import persona_data_dir
from playground.types import Persona

#: A bare snake_case / lowercase enum token (``financial_manager``, ``graduate``)
#: — humanized for display. Anything with a space, hyphen, uppercase, or other
#: punctuation (cities, sentences, ids) is left exactly as authored.
_ENUM_VALUE_RE = re.compile(r"[a-z0-9]+(?:_[a-z0-9]+)*")

# Canonical persona source: the checked-in Playground dev pool.
_CURATED_DIR = persona_data_dir(Path(__file__))

# Keys that are loader bookkeeping rather than persona content.
_SKIP_KEYS = {"id", "persona_id", "version", "source", "source_file", "raw_fields"}


def _normalize_persona_id(value: str) -> str:
    text = str(value).strip()
    if not text:
        return text
    if text.startswith("persona_"):
        suffix = text.removeprefix("persona_")
        return suffix.zfill(4) if suffix.isdigit() else suffix
    return text.zfill(4) if text.isdigit() else text


def _humanize(label: str) -> str:
    """Turn a snake_case / lowercase key into a "Humanized Label"."""
    text = str(label).replace("_", " ").strip()
    if not text:
        return text
    return " ".join(
        w if (w[:1].isupper() or not w[:1].isalpha()) else w.capitalize()
        for w in text.split(" ")
    )


def _render(value: Any, indent: int = 0) -> List[str]:
    """Recursively render a scalar / list / dict into indented text lines."""
    pad = "  " * indent
    lines: List[str] = []
    if isinstance(value, dict):
        for key, val in value.items():
            label = _humanize(key)
            if isinstance(val, (dict, list)):
                lines.append("{}{}:".format(pad, label))
                lines.extend(_render(val, indent + 1))
            else:
                rendered = _render_scalar(val)
                if rendered:
                    lines.append("{}{}: {}".format(pad, label, rendered))
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)):
                lines.extend(_render(item, indent))
            else:
                rendered = _render_scalar(item)
                if rendered:
                    lines.append("{}- {}".format(pad, rendered))
    else:
        rendered = _render_scalar(value)
        if rendered:
            lines.append("{}{}".format(pad, rendered))
    return lines


def _render_scalar(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return text
    if _ENUM_VALUE_RE.fullmatch(text):
        return _humanize(text)
    return text


def _render_context(data: Dict[str, Any]) -> str:
    """Render a curated persona dict into an indented humanized text block."""
    filtered = {k: v for k, v in data.items() if k not in _SKIP_KEYS}
    return "\n".join(_render(filtered)).strip()


def _extract_name(source: str, data: Dict[str, Any]) -> str:
    """Derive a display name from a canonical persona record."""
    display_name = str(data.get("display_name") or "").strip()
    if display_name:
        return display_name
    persona_id = _normalize_persona_id(
        str(data.get("persona_id") or data.get("id") or "")
    )
    if persona_id:
        return "persona-{}".format(persona_id)
    id_suffix = str(data.get("id", "")).strip() or "unknown"
    return "{} · {}".format(source or "persona", id_suffix)


def _persona_context(data: Dict[str, Any], *, fallback_name: str) -> str:
    rendered = _render_context(data)
    if rendered:
        return rendered
    for key in ("system_prompt", "summary", "display_name", "name"):
        text = str(data.get(key) or "").strip()
        if text:
            return text
    return fallback_name


_CURATED_CACHE: List[Persona] | None = None
_PERSONAS_BY_ID: Dict[str, Persona] | None = None


def clear_persona_catalog_cache() -> None:
    """Drop in-process curated persona cache (tests / pool reloads)."""
    global _CURATED_CACHE, _PERSONAS_BY_ID
    _CURATED_CACHE = None
    _PERSONAS_BY_ID = None


def _load_curated() -> List[Persona]:
    global _CURATED_CACHE
    if _CURATED_CACHE is not None:
        return _CURATED_CACHE
    personas: List[Persona] = []
    if not _CURATED_DIR.exists():
        _CURATED_CACHE = personas
        return personas
    for path in sorted(_CURATED_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            continue
        source = str(data.get("source", "")).strip()
        persona_id = _normalize_persona_id(
            str(data.get("persona_id") or data.get("id") or path.stem)
        )
        name = _extract_name(source, data)
        persona = Persona(
            id=persona_id or path.stem,
            name=name,
            source=source,
            context=_persona_context(data, fallback_name=name),
        )
        personas.append(persona)
    _CURATED_CACHE = personas
    return personas


def _load_all() -> Dict[str, Persona]:
    global _PERSONAS_BY_ID
    if _PERSONAS_BY_ID is not None:
        return _PERSONAS_BY_ID
    personas: Dict[str, Persona] = {}
    for persona in _load_curated():
        personas[persona.id] = persona
        normalized = _normalize_persona_id(persona.id)
        if normalized and normalized not in personas:
            personas[normalized] = persona
        if persona.id.isdigit():
            stem = "persona_{}".format(persona.id.zfill(4))
            personas.setdefault(stem, persona)
    _PERSONAS_BY_ID = personas
    return personas


def load_personas(query: str = "", limit: Optional[int] = None) -> List[Persona]:
    personas = sorted(_load_curated(), key=lambda p: p.id)
    if query:
        needle = query.lower()
        personas = [p for p in personas if needle in (p.name + " " + p.context).lower()]
    if limit is not None:
        personas = personas[:limit]
    return personas


def get_persona(persona_id: str) -> Persona:
    personas = _load_all()
    key = persona_id.strip()
    normalized = _normalize_persona_id(key)
    if key in personas:
        return personas[key]
    if normalized in personas:
        return personas[normalized]
    raise KeyError("unknown persona: {}".format(persona_id))
