"""Correct use.computer Anthropic CUA tool/beta selection for newer Claude models.

``use-computer==0.0.44`` only enables ``computer_20251124`` when the model name
contains ``opus-4-6`` or ``sonnet-4-6``. That mis-routes ``claude-opus-4-8``
(and other post-4.5 models) onto the legacy ``computer_20250124`` tool, which
Anthropic rejects with HTTP 400.

Harbor's Docker ``computer-1`` path already uses
:func:`harbor.agents.computer_1.providers.anthropic.cua_protocol_for_model`.
This module applies the same mapping to use.computer's ``AnthropicCUAAgent``
without forking its ``_run_agent`` body.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

_PATCH_ATTR = "_matraix_cua_protocol_patched"


def rewrite_computer_tools(
    tools: Sequence[Any],
    tool_type: str,
) -> list[Any]:
    """Return tools with computer_* type entries rewritten to ``tool_type``."""
    rewritten: list[Any] = []
    for tool in tools:
        if isinstance(tool, Mapping) and str(tool.get("type", "")).startswith(
            "computer_"
        ):
            entry = dict(tool)
            entry["type"] = tool_type
            rewritten.append(entry)
        else:
            rewritten.append(tool)
    return rewritten


def correct_anthropic_cua_create_kwargs(
    kwargs: Mapping[str, Any],
) -> dict[str, Any]:
    """Rewrite Anthropic beta ``messages.create`` kwargs to the Harbor CUA protocol.

    Uses :func:`harbor.agents.computer_1.providers.anthropic.cua_protocol_for_model`
    so Opus 4.8+ / Sonnet 4.6+ get ``computer_20251124``, while Haiku 4.5 /
    Sonnet 4.5 stay on the legacy tool.
    """
    from harbor.agents.computer_1.providers.anthropic import cua_protocol_for_model

    out = dict(kwargs)
    model = out.get("model")
    if not isinstance(model, str) or not model.strip():
        return out

    beta, tool_type = cua_protocol_for_model(model)
    out["betas"] = [beta]
    tools = out.get("tools")
    if tools is not None:
        out["tools"] = rewrite_computer_tools(list(tools), tool_type)
    return out


def apply_use_computer_anthropic_cua_protocol_patch() -> bool:
    """Monkeypatch use.computer ``AnthropicCUAAgent`` create kwargs (idempotent).

    Returns True when the patch was newly applied, False if already patched or
    use.computer is unavailable.
    """
    try:
        from use_computer.agents.providers.anthropic import AnthropicCUAAgent
    except ModuleNotFoundError:
        return False

    if getattr(AnthropicCUAAgent, _PATCH_ATTR, False):
        return False

    from anthropic.resources.beta.messages.messages import Messages

    original_run = AnthropicCUAAgent._run_agent
    original_create = Messages.create

    def _patched_create(self: Any, *args: Any, **kwargs: Any) -> Any:
        return original_create(self, *args, **correct_anthropic_cua_create_kwargs(kwargs))

    async def _patched_run(
        self: Any,
        instruction: str,
        environment: Any,
        context: Any,
    ) -> None:
        previous = Messages.create
        Messages.create = _patched_create  # type: ignore[method-assign]
        try:
            await original_run(self, instruction, environment, context)
        finally:
            Messages.create = previous  # type: ignore[method-assign]

    AnthropicCUAAgent._run_agent = _patched_run  # type: ignore[method-assign]
    setattr(AnthropicCUAAgent, _PATCH_ATTR, True)
    return True
