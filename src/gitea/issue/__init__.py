"""Gitea Issue resource."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gitea._lazy import lazy_reexports

if TYPE_CHECKING:
    from gitea.issue.async_issue import AsyncIssue
    from gitea.issue.issue import Issue
    from gitea.issue.project_column import (
        async_column_holds_card,
        column_holds_card,
        find_async_card_column_id,
        find_card_column_id,
        resolve_async_project_column_ids,
        resolve_project_column_ids,
    )

__all__ = [
    "AsyncIssue",
    "Issue",
    "async_column_holds_card",
    "column_holds_card",
    "find_async_card_column_id",
    "find_card_column_id",
    "resolve_async_project_column_ids",
    "resolve_project_column_ids",
]

# Re-exported when a name is first read, not imported here: a submodule reaching a
# sibling by its dotted name imports its package on the way in, so importing them here
# would put each of them in an import cycle. `gitea._lazy` carries the reasoning.
_ORIGINS = {
    "AsyncIssue": "gitea.issue.async_issue",
    "Issue": "gitea.issue.issue",
    "async_column_holds_card": "gitea.issue.project_column",
    "column_holds_card": "gitea.issue.project_column",
    "find_async_card_column_id": "gitea.issue.project_column",
    "find_card_column_id": "gitea.issue.project_column",
    "resolve_async_project_column_ids": "gitea.issue.project_column",
    "resolve_project_column_ids": "gitea.issue.project_column",
}

__getattr__, __dir__ = lazy_reexports(globals(), _ORIGINS)
