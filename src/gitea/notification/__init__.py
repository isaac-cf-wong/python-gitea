"""Gitea Notification resource."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gitea._lazy import lazy_reexports

if TYPE_CHECKING:
    from gitea.notification.async_notification import AsyncNotification
    from gitea.notification.notification import Notification

__all__ = ["AsyncNotification", "Notification"]

# Re-exported when a name is first read, not imported here: a submodule reaching a
# sibling by its dotted name imports its package on the way in, so importing them here
# would put each of them in an import cycle. `gitea._lazy` carries the reasoning.
_ORIGINS = {
    "AsyncNotification": "gitea.notification.async_notification",
    "Notification": "gitea.notification.notification",
}

__getattr__, __dir__ = lazy_reexports(__name__, _ORIGINS)
