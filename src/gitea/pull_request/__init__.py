"""Pull request API for Gitea."""

from __future__ import annotations

from gitea.pull_request.async_pull_request import AsyncPullRequest
from gitea.pull_request.pull_request import PullRequest

__all__ = ["AsyncPullRequest", "PullRequest"]
