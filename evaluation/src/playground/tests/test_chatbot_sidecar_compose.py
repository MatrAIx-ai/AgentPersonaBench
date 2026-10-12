"""Tests for chatbot sidecar standalone compose generation."""

from __future__ import annotations

from pathlib import Path

import yaml

from playground.inprocess.chatbot_sidecar_compose import write_standalone_sidecar_compose


def test_write_standalone_includes_companion_services_from_source(tmp_path: Path) -> None:
    compose_dir = tmp_path / "sidecar"
    compose_dir.mkdir()
    (compose_dir / "docker-compose.yaml").write_text(
        "\n".join(
            [
                "services:",
                "  main:",
                "    depends_on:",
                "      finance-chatbot:",
                "        condition: service_healthy",
                "  finance-chatbot:",
                "    build:",
                "      context: ./finance-chatbot",
                "    depends_on:",
                "      openbb-mcp:",
                "        condition: service_healthy",
                "  openbb-mcp:",
                "    build:",
                "      context: ./openbb-mcp",
                "volumes:",
                "  openbb-cache:",
            ]
        ),
        encoding="utf-8",
    )

    path = write_standalone_sidecar_compose(
        compose_dir=compose_dir,
        service_name="finance-chatbot",
        build_context="finance-chatbot",
        host_port=8901,
    )
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert "main" not in payload["services"]
    assert "finance-chatbot" in payload["services"]
    assert "openbb-mcp" in payload["services"]
    assert payload["services"]["finance-chatbot"]["ports"] == [
        "127.0.0.1:8901:8000"
    ]
    assert "volumes" in payload
