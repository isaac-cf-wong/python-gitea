"""Gitea Comment resource."""

from __future__ import annotations

from gitea.comment.async_comment import AsyncComment
from gitea.comment.comment import Comment

__all__ = ["AsyncComment", "Comment"]
