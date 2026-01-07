"""Client for Gitea API."""

from __future__ import annotations

from gitea.client.async_gitea import AsyncGitea
from gitea.client.gitea import Gitea

__all__ = ["AsyncGitea", "Gitea"]
