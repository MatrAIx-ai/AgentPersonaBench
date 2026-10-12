"""Generate sidecar-only docker compose files (no invalid Harbor ``main`` service)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def write_standalone_sidecar_compose(
    *,
    compose_dir: Path,
    service_name: str,
    build_context: str,
    host_port: int | None = None,
    container_port: int = 8000,
    port_mapping: str | None = None,
    output_dir: Path | None = None,
    source_compose: Path | None = None,
) -> Path:
    """Write a compose file containing the chat API sidecar (and companions).

    When ``source_compose`` exists and defines multiple non-``main`` services,
    copy those services into the standalone file so ``depends_on`` companions
    (for example a product SUT behind an API adapter) start together.
    """
    target_dir = output_dir or (compose_dir / ".playground_sidecar")
    target_dir.mkdir(parents=True, exist_ok=True)
    compose_path = target_dir / "standalone-compose.yaml"
    if port_mapping is None:
        if host_port is None:
            raise ValueError("host_port is required when port_mapping is not set")
        port_mapping = "127.0.0.1:{}:{}".format(host_port, container_port)

    source = source_compose or (compose_dir / "docker-compose.yaml")
    if source.is_file():
        payload = _standalone_from_source(
            source_compose=source,
            primary_service=service_name,
            port_mapping=port_mapping,
            fallback_build_context=build_context,
            container_port=container_port,
        )
    else:
        payload = {
            "services": {
                service_name: {
                    "build": {"context": build_context},
                    "ports": [port_mapping],
                    "healthcheck": _tcp_healthcheck(container_port),
                }
            }
        }

    compose_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return compose_path


def _tcp_healthcheck(container_port: int) -> dict[str, Any]:
    return {
        "test": [
            "CMD",
            "python",
            "-c",
            (
                "import socket; "
                "s=socket.create_connection(('localhost', {}), timeout=2); "
                "s.close()"
            ).format(container_port),
        ],
        "interval": "2s",
        "timeout": "5s",
        "retries": 15,
        "start_period": "5s",
    }


def _standalone_from_source(
    *,
    source_compose: Path,
    primary_service: str,
    port_mapping: str,
    fallback_build_context: str,
    container_port: int,
) -> dict[str, Any]:
    raw = yaml.safe_load(source_compose.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raw = {}
    services_in = raw.get("services")
    if not isinstance(services_in, dict):
        services_in = {}

    companions = {
        name: dict(spec)
        for name, spec in services_in.items()
        if name != "main" and isinstance(spec, dict)
    }
    if not companions:
        companions = {
            primary_service: {
                "build": {"context": fallback_build_context},
                "healthcheck": _tcp_healthcheck(container_port),
            }
        }

    if primary_service not in companions:
        raise ValueError(
            "primary sidecar service {!r} missing from {}".format(
                primary_service, source_compose
            )
        )

    services: dict[str, Any] = {}
    for name, spec in companions.items():
        cleaned = dict(spec)
        cleaned.pop("profiles", None)
        if name == primary_service:
            cleaned["ports"] = [port_mapping]
            cleaned.setdefault("healthcheck", _tcp_healthcheck(container_port))
        services[name] = cleaned

    payload: dict[str, Any] = {"services": services}
    volumes = raw.get("volumes")
    if isinstance(volumes, dict) and volumes:
        payload["volumes"] = volumes
    return payload
