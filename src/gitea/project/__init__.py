"""Gitea Project resource."""

from __future__ import annotations

from gitea.project.async_project import AsyncProject
from gitea.project.project import Project

__all__ = ["AsyncProject", "Project"]
