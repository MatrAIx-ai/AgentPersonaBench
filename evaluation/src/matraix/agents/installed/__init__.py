"""Playground-installed agents for Docker web scenarios."""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = [
    "BrowserUseHarborAgent",
    "CocoaHarborAgent",
]

if TYPE_CHECKING:
    from matraix.agents.installed.browser_use import BrowserUseHarborAgent
    from matraix.agents.installed.cocoa import CocoaHarborAgent

_LAZY_IMPORTS = {
    "BrowserUseHarborAgent": (
        "matraix.agents.installed.browser_use",
        "BrowserUseHarborAgent",
    ),
    "CocoaHarborAgent": ("matraix.agents.installed.cocoa", "CocoaHarborAgent"),
}


def __getattr__(name: str):
    if name not in _LAZY_IMPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_path, attr_name = _LAZY_IMPORTS[name]
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, attr_name)
