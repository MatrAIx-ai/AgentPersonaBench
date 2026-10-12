"""Resolve the persona LLM for Harbor host-native and in-process eval paths."""

from __future__ import annotations

import os

from playground.types import DEFAULT_PERSONA_MODEL


def resolve_persona_model(
    *,
    model_name: str | None = None,
    include_chat_env: bool = False,
) -> str:
    """Return the persona model id for a trial.

    Precedence matches Docker/web Harbor agents (``browser-use``, ``computer-1``):

    1. Harbor job ``agents[].model_name`` or CLI ``-m`` (``model_name`` argument)
    2. ``MATRIX_CHATBOT_PERSONA_MODEL`` when ``include_chat_env`` is true
    3. ``MATRIX_PERSONA_MODEL`` / ``MATRIX_HARBOR_PERSONA_MODEL`` via config helper
    4. ``DEFAULT_PERSONA_MODEL``
    """
    if isinstance(model_name, str) and model_name.strip():
        return model_name.strip()
    if include_chat_env:
        chat_model = os.environ.get("MATRIX_CHATBOT_PERSONA_MODEL", "").strip()
        if chat_model:
            return chat_model
    try:
        from backend.service.config import persona_model as _persona_model

        return _persona_model()
    except ImportError:
        for key in ("MATRIX_PERSONA_MODEL", "MATRIX_HARBOR_PERSONA_MODEL"):
            value = os.environ.get(key, "").strip()
            if value:
                return value
        return DEFAULT_PERSONA_MODEL
