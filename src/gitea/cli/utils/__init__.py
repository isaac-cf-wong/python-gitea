"""Utility functions for Gitea CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gitea._lazy import lazy_reexports

if TYPE_CHECKING:
    from gitea.cli.utils.api import execute_api_command
    from gitea.cli.utils.auth import get_auth_params

__all__ = ["execute_api_command", "get_auth_params"]

# Re-exported when a name is first read, not imported here: a submodule reaching a
# sibling by its dotted name imports its package on the way in, so importing them here
# would put each of them in an import cycle. `gitea._lazy` carries the reasoning.
_ORIGINS = {
    "execute_api_command": "gitea.cli.utils.api",
    "get_auth_params": "gitea.cli.utils.auth",
}

__getattr__, __dir__ = lazy_reexports(__name__, _ORIGINS)
