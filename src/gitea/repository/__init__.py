"""Repository package."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gitea._lazy import lazy_reexports

if TYPE_CHECKING:
    from gitea.repository.async_repository import AsyncRepository
    from gitea.repository.repository import Repository

__all__ = ["AsyncRepository", "Repository"]

# Re-exported when a name is first read, not imported here: a submodule reaching a
# sibling by its dotted name imports its package on the way in, so importing them here
# would put each of them in an import cycle. `gitea._lazy` carries the reasoning.
_ORIGINS = {
    "AsyncRepository": "gitea.repository.async_repository",
    "Repository": "gitea.repository.repository",
}

__getattr__, __dir__ = lazy_reexports(__name__, _ORIGINS)
