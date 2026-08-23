"""Gitea Comment resource."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gitea._lazy import lazy_reexports

if TYPE_CHECKING:
    from gitea.comment.async_comment import AsyncComment
    from gitea.comment.comment import Comment

__all__ = ["AsyncComment", "Comment"]

# Re-exported when a name is first read, not imported here: a submodule reaching a
# sibling by its dotted name imports its package on the way in, so importing them here
# would put each of them in an import cycle. `gitea._lazy` carries the reasoning.
_ORIGINS = {
    "AsyncComment": "gitea.comment.async_comment",
    "Comment": "gitea.comment.comment",
}

__getattr__, __dir__ = lazy_reexports(globals(), _ORIGINS)
