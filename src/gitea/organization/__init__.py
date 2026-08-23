"""Organization package."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gitea._lazy import lazy_reexports

if TYPE_CHECKING:
    from gitea.organization.async_organization import AsyncOrganization
    from gitea.organization.organization import Organization

__all__ = ["AsyncOrganization", "Organization"]

# Re-exported when a name is first read, not imported here: a submodule reaching a
# sibling by its dotted name imports its package on the way in, so importing them here
# would put each of them in an import cycle. `gitea._lazy` carries the reasoning.
_ORIGINS = {
    "AsyncOrganization": "gitea.organization.async_organization",
    "Organization": "gitea.organization.organization",
}

__getattr__, __dir__ = lazy_reexports(__name__, _ORIGINS)
