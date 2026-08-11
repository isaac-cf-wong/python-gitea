"""Gitea Milestone resource."""

from __future__ import annotations

from gitea.milestone.async_milestone import AsyncMilestone
from gitea.milestone.milestone import Milestone

__all__ = ["AsyncMilestone", "Milestone"]
