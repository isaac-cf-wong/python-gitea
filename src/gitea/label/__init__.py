"""Gitea Label resource."""

from __future__ import annotations

from gitea.label.async_label import AsyncLabel
from gitea.label.label import Label

__all__ = ["AsyncLabel", "Label"]
