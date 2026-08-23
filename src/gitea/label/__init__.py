"""Gitea Label resource."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gitea._lazy import lazy_reexports

if TYPE_CHECKING:
    from gitea.label.async_label import AsyncLabel
    from gitea.label.label import Label

__all__ = ["AsyncLabel", "Label"]

# Re-exported when a name is first read, not imported here: a submodule reaching a
# sibling by its dotted name imports its package on the way in, so importing them here
# would put each of them in an import cycle. `gitea._lazy` carries the reasoning.
_ORIGINS = {
    "AsyncLabel": "gitea.label.async_label",
    "Label": "gitea.label.label",
}

__getattr__, __dir__ = lazy_reexports(globals(), _ORIGINS)
