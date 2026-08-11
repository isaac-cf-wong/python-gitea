"""Gitea Notification resource."""

from __future__ import annotations

from gitea.notification.async_notification import AsyncNotification
from gitea.notification.notification import Notification

__all__ = ["AsyncNotification", "Notification"]
