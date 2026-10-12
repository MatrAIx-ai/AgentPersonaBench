"""Task-declared chatbot capabilities for UserSim and Harbor persona agents.

Contract names (one concept):
- yaml section: ``structuredExposure.fields[]``
- capability id: ``structured_exposure`` (list in ``capabilities``; also
  auto-added when exposure fields exist)
- turn wire field: ``structuredExposure``

Shared chat always includes text messaging plus the UserSim control tool
``end_conversation``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class ChatbotCapabilityHttp:
    method: str = "POST"
    path: str = ""


@dataclass(frozen=True)
class ChatbotCapability:
    """One product capability exposed to the simulated user / persona agent."""

    id: str
    label: str
    description: str = ""
    kind: str = "action"  # action | exposure
    tool: str = ""  # UserSim / MCP tool name; empty for exposure-only
    http: ChatbotCapabilityHttp | None = None

    def to_public_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "kind": self.kind,
        }
        if self.tool:
            payload["tool"] = self.tool
        if self.http is not None and self.http.path:
            payload["http"] = {
                "method": self.http.method,
                "path": self.http.path,
            }
        return payload


_TEXT_CHAT = ChatbotCapability(
    id="text_chat",
    label="Text chat",
    description="Send natural-language messages to the application chatbot.",
    kind="action",
    tool="send_message",
    http=ChatbotCapabilityHttp(method="POST", path="/v1/messages"),
)

STRUCTURED_EXPOSURE = ChatbotCapability(
    id="structured_exposure",
    label="Structured reply details",
    description=(
        "The chatbot may attach structured details in its replies; "
        "inspect task-configured structuredExposure.fields after each turn."
    ),
    kind="exposure",
    tool="",
)

_KNOWN: dict[str, ChatbotCapability] = {
    "text_chat": _TEXT_CHAT,
    "structured_exposure": STRUCTURED_EXPOSURE,
    "upload_image": ChatbotCapability(
        id="upload_image",
        label="Image upload",
        description=(
            "Upload a medical image (PNG/JPG) with optional text when the product "
            "asks for or would benefit from an image."
        ),
        kind="action",
        tool="upload_image",
        http=ChatbotCapabilityHttp(method="POST", path="/v1/upload"),
    ),
    "validate_output": ChatbotCapability(
        id="validate_output",
        label="Validate output",
        description=(
            "Confirm or reject a medical AI output when the product asks for "
            "human validation."
        ),
        kind="action",
        tool="validate_output",
        http=ChatbotCapabilityHttp(method="POST", path="/v1/validate"),
    ),
}


def default_capabilities() -> tuple[ChatbotCapability, ...]:
    return (_TEXT_CHAT,)


def parse_capabilities(raw: Any) -> tuple[ChatbotCapability, ...]:
    """Parse ``capabilities`` from chatbot.yaml.

    Accepts a list of capability ids (strings) or mapping objects with at least
    ``id``. Unknown ids are kept as custom action capabilities when ``tool`` or
    ``http.path`` is provided.
    """
    if raw is None:
        return default_capabilities()
    if not isinstance(raw, list) or not raw:
        return default_capabilities()

    out: list[ChatbotCapability] = []
    seen: set[str] = set()
    for entry in raw:
        capability = _parse_one(entry)
        if capability is None or capability.id in seen:
            continue
        seen.add(capability.id)
        out.append(capability)
    if "text_chat" not in seen:
        out.insert(0, _TEXT_CHAT)
    return tuple(out) if out else default_capabilities()


def with_structured_exposure_capability(
    capabilities: Sequence[ChatbotCapability],
    *,
    has_exposure_fields: bool,
) -> tuple[ChatbotCapability, ...]:
    """Ensure capability ``structured_exposure`` when yaml defines exposure fields."""
    caps = list(capabilities) if capabilities else list(default_capabilities())
    ids = {item.id for item in caps}
    if has_exposure_fields and "structured_exposure" not in ids:
        caps.append(STRUCTURED_EXPOSURE)
    if "text_chat" not in ids:
        caps.insert(0, _TEXT_CHAT)
    return tuple(caps)


def _parse_one(entry: Any) -> ChatbotCapability | None:
    if isinstance(entry, str):
        key = entry.strip()
        if not key:
            return None
        known = _KNOWN.get(key)
        return known or ChatbotCapability(id=key, label=key.replace("_", " ").title())

    if not isinstance(entry, Mapping):
        return None
    capability_id = str(entry.get("id") or "").strip()
    if not capability_id:
        return None
    known = _KNOWN.get(capability_id)
    http_raw = entry.get("http")
    http = None
    if isinstance(http_raw, Mapping):
        path = str(http_raw.get("path") or "").strip()
        if path:
            http = ChatbotCapabilityHttp(
                method=(str(http_raw.get("method") or "POST").strip() or "POST").upper(),
                path=path,
            )
    label = str(entry.get("label") or "").strip()
    description = str(entry.get("description") or "").strip()
    kind = str(entry.get("kind") or "").strip()
    tool = str(entry.get("tool") or "").strip()
    if known is not None:
        return ChatbotCapability(
            id=known.id,
            label=label or known.label,
            description=description or known.description,
            kind=kind or known.kind,
            tool=tool if "tool" in entry else known.tool,
            http=http if http is not None else known.http,
        )
    return ChatbotCapability(
        id=capability_id,
        label=label or capability_id.replace("_", " ").title(),
        description=description,
        kind=kind or ("exposure" if not tool and http is None else "action"),
        tool=tool,
        http=http,
    )


def capability_ids(capabilities: Sequence[ChatbotCapability]) -> tuple[str, ...]:
    return tuple(item.id for item in capabilities)


def action_capabilities(
    capabilities: Sequence[ChatbotCapability],
) -> tuple[ChatbotCapability, ...]:
    return tuple(item for item in capabilities if item.kind == "action" and item.tool)


def capability_by_tool(
    capabilities: Sequence[ChatbotCapability], tool_name: str
) -> ChatbotCapability | None:
    for item in capabilities:
        if item.tool == tool_name:
            return item
    return None


def capability_by_id(
    capabilities: Sequence[ChatbotCapability], capability_id: str
) -> ChatbotCapability | None:
    for item in capabilities:
        if item.id == capability_id:
            return item
    return None
