"""Initialization of the configuration module for gitea."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gitea._lazy import lazy_reexports

if TYPE_CHECKING:
    from gitea.config.manager import ConfigManager
    from gitea.config.model import AccountConfig, Config

__all__ = ["AccountConfig", "Config", "ConfigManager"]

# Re-exported when a name is first read, not imported here: a submodule reaching a
# sibling by its dotted name imports its package on the way in, so importing them here
# would put each of them in an import cycle. `gitea._lazy` carries the reasoning.
_ORIGINS = {
    "AccountConfig": "gitea.config.model",
    "Config": "gitea.config.model",
    "ConfigManager": "gitea.config.manager",
}

__getattr__, __dir__ = lazy_reexports(__name__, _ORIGINS)
