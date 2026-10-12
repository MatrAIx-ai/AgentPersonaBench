from __future__ import annotations

from backend.service.application_types import normalize_metadata_type


def test_normalize_metadata_type_maps_legacy_aliases() -> None:
    assert normalize_metadata_type("chat") == "chatbot"
    assert normalize_metadata_type("cua") == "os-app"
    assert normalize_metadata_type("os_app") == "os-app"
    assert normalize_metadata_type("desktop") == "os-app"
    assert normalize_metadata_type("mobile") == "os-app"


def test_normalize_metadata_type_preserves_canonical_values() -> None:
    assert normalize_metadata_type("chatbot") == "chatbot"
    assert normalize_metadata_type("os-app") == "os-app"
    assert normalize_metadata_type("survey") == "survey"
    assert normalize_metadata_type("web") == "web"
