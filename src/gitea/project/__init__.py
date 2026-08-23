"""Gitea Project resource."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gitea._lazy import lazy_reexports

if TYPE_CHECKING:
    from gitea.project.async_project import AsyncProject
    from gitea.project.project import Project

__all__ = ["AsyncProject", "Project"]

# Re-exported when a name is first read, not imported here: a submodule reaching a
# sibling by its dotted name imports its package on the way in, so importing them here
# would put each of them in an import cycle. `gitea._lazy` carries the reasoning.
_ORIGINS = {
    "AsyncProject": "gitea.project.async_project",
    "Project": "gitea.project.project",
}

__getattr__, __dir__ = lazy_reexports(__name__, _ORIGINS)
