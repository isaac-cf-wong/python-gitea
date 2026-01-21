"""Gitea Issue resource."""

from __future__ import annotations

from gitea.issue.async_issue import AsyncIssue
from gitea.issue.issue import Issue

__all__ = ["AsyncIssue", "Issue"]
