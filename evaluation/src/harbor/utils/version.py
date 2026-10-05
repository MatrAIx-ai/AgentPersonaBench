from __future__ import annotations

import importlib.metadata

_DISTRIBUTION_NAMES = ("harbor", "matraix")


def get_harbor_version(default: str | None = None) -> str | None:
    for distribution_name in _DISTRIBUTION_NAMES:
        try:
            return importlib.metadata.version(distribution_name)
        except importlib.metadata.PackageNotFoundError:
            continue
    return default


def get_harbor_distribution() -> importlib.metadata.Distribution | None:
    for distribution_name in _DISTRIBUTION_NAMES:
        try:
            return importlib.metadata.distribution(distribution_name)
        except importlib.metadata.PackageNotFoundError:
            continue
    return None
