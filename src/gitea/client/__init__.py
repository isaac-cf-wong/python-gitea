"""Client for Gitea API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gitea._lazy import lazy_reexports

if TYPE_CHECKING:
    from gitea.client.async_gitea import AsyncGitea
    from gitea.client.gitea import Gitea

__all__ = ["AsyncGitea", "Gitea"]

# Re-exported when a name is first read, not imported here: a submodule reaching a
# sibling by its dotted name imports its package on the way in, so importing them here
# would put each of them in an import cycle. `gitea._lazy` carries the reasoning.
_ORIGINS = {
    "AsyncGitea": "gitea.client.async_gitea",
    "Gitea": "gitea.client.gitea",
}

__getattr__, __dir__ = lazy_reexports(__name__, _ORIGINS)
