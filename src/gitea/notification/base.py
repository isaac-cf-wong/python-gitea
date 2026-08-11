"""Base class for Gitea Notification resource."""

from __future__ import annotations

from datetime import datetime
from typing import Any


class BaseNotification:
    """Base class for Gitea Notification resource."""

    def _list_notifications_endpoint(self) -> str:
        """Construct the endpoint URL for listing notifications.

        Returns:
            The endpoint URL for listing notifications.

        """
        return "/notifications"

    def _list_notifications_helper(
        self,
        all_notifications: bool | None = None,
        status_types: list[str] | None = None,
        subject_type: list[str] | None = None,
        since: datetime | None = None,
        before: datetime | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for listing notifications.

        Args:
            all_notifications: If true, show notifications marked as read.
            status_types: Show notifications with the provided status types.
            subject_type: Filter notifications by subject type.
            since: Only show notifications updated after the given time.
            before: Only show notifications updated before the given time.
            page: The page number for pagination.
            limit: The number of notifications per page.

        Returns:
            A tuple containing the endpoint and the request arguments.

        """
        endpoint = self._list_notifications_endpoint()

        params: dict[str, Any] = {}
        if all_notifications is not None:
            params["all"] = all_notifications
        if status_types is not None:
            params["status-types"] = status_types
        if subject_type is not None:
            params["subject-type"] = subject_type
        if since is not None:
            params["since"] = since.isoformat()
        if before is not None:
            params["before"] = before.isoformat()
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit

        return endpoint, params

    def _list_repo_notifications_endpoint(self, owner: str, repository: str) -> str:
        """Construct the endpoint URL for listing repository notifications.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.

        Returns:
            The endpoint URL for listing repository notifications.

        """
        return f"/repos/{owner}/{repository}/notifications"

    def _list_repo_notifications_helper(
        self,
        owner: str,
        repository: str,
        all_notifications: bool | None = None,
        status_types: list[str] | None = None,
        subject_type: list[str] | None = None,
        since: datetime | None = None,
        before: datetime | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for listing repository notifications.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            all_notifications: If true, show notifications marked as read.
            status_types: Show notifications with the provided status types.
            subject_type: Filter notifications by subject type.
            since: Only show notifications updated after the given time.
            before: Only show notifications updated before the given time.
            page: The page number for pagination.
            limit: The number of notifications per page.

        Returns:
            A tuple containing the endpoint and the request arguments.

        """
        endpoint = self._list_repo_notifications_endpoint(owner=owner, repository=repository)

        params: dict[str, Any] = {}
        if all_notifications is not None:
            params["all"] = all_notifications
        if status_types is not None:
            params["status-types"] = status_types
        if subject_type is not None:
            params["subject-type"] = subject_type
        if since is not None:
            params["since"] = since.isoformat()
        if before is not None:
            params["before"] = before.isoformat()
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit

        return endpoint, params

    def _read_notifications_helper(
        self,
        last_read_at: datetime | None = None,
        all_notifications: bool | None = None,
        status_types: list[str] | None = None,
        to_status: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for marking notifications as read.

        Args:
            last_read_at: Describes the last point that notifications were checked.
            all_notifications: If true, mark all notifications on this repo.
            status_types: Mark notifications with the provided status types as read.
            to_status: Status to mark notifications as.

        Returns:
            A tuple containing the endpoint and the request arguments.

        """
        endpoint = self._list_notifications_endpoint()

        params: dict[str, Any] = {}
        if last_read_at is not None:
            params["last_read_at"] = last_read_at.isoformat()
        if all_notifications is not None:
            params["all"] = all_notifications
        if status_types is not None:
            params["status-types"] = status_types
        if to_status is not None:
            params["to-status"] = to_status

        return endpoint, params

    def _read_repo_notifications_helper(
        self,
        owner: str,
        repository: str,
        last_read_at: datetime | None = None,
        all_notifications: bool | None = None,
        status_types: list[str] | None = None,
        to_status: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for marking repository notifications as read.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            last_read_at: Describes the last point that notifications were checked.
            all_notifications: If true, mark all notifications on this repo.
            status_types: Mark notifications with the provided status types as read.
            to_status: Status to mark notifications as.

        Returns:
            A tuple containing the endpoint and the request arguments.

        """
        endpoint = self._list_repo_notifications_endpoint(owner=owner, repository=repository)

        params: dict[str, Any] = {}
        if last_read_at is not None:
            params["last_read_at"] = last_read_at.isoformat()
        if all_notifications is not None:
            params["all"] = all_notifications
        if status_types is not None:
            params["status-types"] = status_types
        if to_status is not None:
            params["to-status"] = to_status

        return endpoint, params

    def _get_notification_thread_endpoint(self, thread_id: int) -> str:
        """Construct the endpoint URL for getting a notification thread.

        Args:
            thread_id: The ID of the notification thread.

        Returns:
            The endpoint URL for getting the notification thread.

        """
        return f"/notifications/threads/{thread_id}"

    def _get_notification_thread_helper(self, thread_id: int) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for getting a notification thread.

        Args:
            thread_id: The ID of the notification thread.

        Returns:
            A tuple containing the endpoint and the request arguments.

        """
        endpoint = self._get_notification_thread_endpoint(thread_id=thread_id)
        return endpoint, {}

    def _read_notification_thread_helper(
        self,
        thread_id: int,
        to_status: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for marking a notification thread.

        Args:
            thread_id: The ID of the notification thread.
            to_status: Status to mark notifications as.

        Returns:
            A tuple containing the endpoint and the request arguments.

        """
        endpoint = self._get_notification_thread_endpoint(thread_id=thread_id)

        params: dict[str, Any] = {}
        if to_status is not None:
            params["to-status"] = to_status

        return endpoint, params

    def _new_notifications_endpoint(self) -> str:
        """Construct the endpoint URL for counting new notifications.

        Returns:
            The endpoint URL for counting new notifications.

        """
        return "/notifications/new"
