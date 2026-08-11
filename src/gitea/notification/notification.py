"""Gitea Notification resource."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from requests import Response

from gitea.notification.base import BaseNotification
from gitea.resource.resource import Resource
from gitea.utils.response import process_response


class Notification(BaseNotification, Resource):
    """Gitea Notification resource."""

    def _list_notifications(
        self,
        all_notifications: bool | None = None,
        status_types: list[str] | None = None,
        subject_type: list[str] | None = None,
        since: datetime | None = None,
        before: datetime | None = None,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> Response:
        """List the authenticated user's notifications.

        Args:
            all_notifications: If true, show notifications marked as read.
            status_types: Show notifications with the provided status types.
            subject_type: Filter notifications by subject type.
            since: Only show notifications updated after the given time.
            before: Only show notifications updated before the given time.
            page: The page number for pagination.
            limit: The number of notifications per page.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._list_notifications_helper(
            all_notifications=all_notifications,
            status_types=status_types,
            subject_type=subject_type,
            since=since,
            before=before,
            page=page,
            limit=limit,
        )
        return self._get(endpoint=endpoint, params=params, **kwargs)

    def list_notifications(
        self,
        all_notifications: bool | None = None,
        status_types: list[str] | None = None,
        subject_type: list[str] | None = None,
        since: datetime | None = None,
        before: datetime | None = None,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """List the authenticated user's notifications.

        Args:
            all_notifications: If true, show notifications marked as read.
            status_types: Show notifications with the provided status types.
            subject_type: Filter notifications by subject type.
            since: Only show notifications updated after the given time.
            before: Only show notifications updated before the given time.
            page: The page number for pagination.
            limit: The number of notifications per page.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing a list of notifications as dictionaries and a dictionary with metadata.

        """
        response = self._list_notifications(
            all_notifications=all_notifications,
            status_types=status_types,
            subject_type=subject_type,
            since=since,
            before=before,
            page=page,
            limit=limit,
            **kwargs,
        )
        data, status_code = process_response(response, default=[])
        return cast(list[dict[str, Any]], data), {"status_code": status_code}

    def _list_repo_notifications(
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
        **kwargs: Any,
    ) -> Response:
        """List a repository's notifications.

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
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._list_repo_notifications_helper(
            owner=owner,
            repository=repository,
            all_notifications=all_notifications,
            status_types=status_types,
            subject_type=subject_type,
            since=since,
            before=before,
            page=page,
            limit=limit,
        )
        return self._get(endpoint=endpoint, params=params, **kwargs)

    def list_repo_notifications(
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
        **kwargs: Any,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """List a repository's notifications.

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
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing a list of notifications as dictionaries and a dictionary with metadata.

        """
        response = self._list_repo_notifications(
            owner=owner,
            repository=repository,
            all_notifications=all_notifications,
            status_types=status_types,
            subject_type=subject_type,
            since=since,
            before=before,
            page=page,
            limit=limit,
            **kwargs,
        )
        data, status_code = process_response(response, default=[])
        return cast(list[dict[str, Any]], data), {"status_code": status_code}

    def _read_notifications(
        self,
        last_read_at: datetime | None = None,
        all_notifications: bool | None = None,
        status_types: list[str] | None = None,
        to_status: str | None = None,
        **kwargs: Any,
    ) -> Response:
        """Mark notifications as read.

        Args:
            last_read_at: Describes the last point that notifications were checked.
            all_notifications: If true, mark all notifications on this repo.
            status_types: Mark notifications with the provided status types as read.
            to_status: Status to mark notifications as.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._read_notifications_helper(
            last_read_at=last_read_at,
            all_notifications=all_notifications,
            status_types=status_types,
            to_status=to_status,
        )
        return self._put(endpoint=endpoint, params=params, **kwargs)

    def read_notifications(
        self,
        last_read_at: datetime | None = None,
        all_notifications: bool | None = None,
        status_types: list[str] | None = None,
        to_status: str | None = None,
        **kwargs: Any,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Mark notifications as read.

        Args:
            last_read_at: Describes the last point that notifications were checked.
            all_notifications: If true, mark all notifications on this repo.
            status_types: Mark notifications with the provided status types as read.
            to_status: Status to mark notifications as.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the changed notification threads as a list of dictionaries and a dictionary with metadata.

        """
        response = self._read_notifications(
            last_read_at=last_read_at,
            all_notifications=all_notifications,
            status_types=status_types,
            to_status=to_status,
            **kwargs,
        )
        data, status_code = process_response(response, default=[])
        return cast(list[dict[str, Any]], data), {"status_code": status_code}

    def _read_repo_notifications(
        self,
        owner: str,
        repository: str,
        last_read_at: datetime | None = None,
        all_notifications: bool | None = None,
        status_types: list[str] | None = None,
        to_status: str | None = None,
        **kwargs: Any,
    ) -> Response:
        """Mark a repository's notifications as read.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            last_read_at: Describes the last point that notifications were checked.
            all_notifications: If true, mark all notifications on this repo.
            status_types: Mark notifications with the provided status types as read.
            to_status: Status to mark notifications as.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._read_repo_notifications_helper(
            owner=owner,
            repository=repository,
            last_read_at=last_read_at,
            all_notifications=all_notifications,
            status_types=status_types,
            to_status=to_status,
        )
        return self._put(endpoint=endpoint, params=params, **kwargs)

    def read_repo_notifications(
        self,
        owner: str,
        repository: str,
        last_read_at: datetime | None = None,
        all_notifications: bool | None = None,
        status_types: list[str] | None = None,
        to_status: str | None = None,
        **kwargs: Any,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Mark a repository's notifications as read.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            last_read_at: Describes the last point that notifications were checked.
            all_notifications: If true, mark all notifications on this repo.
            status_types: Mark notifications with the provided status types as read.
            to_status: Status to mark notifications as.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the changed notification threads as a list of dictionaries and a dictionary with metadata.

        """
        response = self._read_repo_notifications(
            owner=owner,
            repository=repository,
            last_read_at=last_read_at,
            all_notifications=all_notifications,
            status_types=status_types,
            to_status=to_status,
            **kwargs,
        )
        data, status_code = process_response(response, default=[])
        return cast(list[dict[str, Any]], data), {"status_code": status_code}

    def _get_notification_thread(
        self,
        thread_id: int,
        **kwargs: Any,
    ) -> Response:
        """Get a notification thread.

        Args:
            thread_id: The ID of the notification thread.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._get_notification_thread_helper(thread_id=thread_id)
        return self._get(endpoint=endpoint, params=params, **kwargs)

    def get_notification_thread(
        self,
        thread_id: int,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Get a notification thread.

        Args:
            thread_id: The ID of the notification thread.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the notification thread as a dictionary and a dictionary with metadata.

        """
        response = self._get_notification_thread(thread_id=thread_id, **kwargs)
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    def _read_notification_thread(
        self,
        thread_id: int,
        to_status: str | None = None,
        **kwargs: Any,
    ) -> Response:
        """Mark a notification thread.

        Args:
            thread_id: The ID of the notification thread.
            to_status: Status to mark notifications as.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._read_notification_thread_helper(
            thread_id=thread_id,
            to_status=to_status,
        )
        return self._patch(endpoint=endpoint, params=params, **kwargs)

    def read_notification_thread(
        self,
        thread_id: int,
        to_status: str | None = None,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Mark a notification thread.

        Args:
            thread_id: The ID of the notification thread.
            to_status: Status to mark notifications as.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the notification thread as a dictionary and a dictionary with metadata.

        """
        response = self._read_notification_thread(
            thread_id=thread_id,
            to_status=to_status,
            **kwargs,
        )
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    def _new_notifications(
        self,
        **kwargs: Any,
    ) -> Response:
        """Count new notifications.

        Args:
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint = self._new_notifications_endpoint()
        return self._get(endpoint=endpoint, **kwargs)

    def new_notifications(
        self,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Count new notifications.

        Args:
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the new notification count as a dictionary and a dictionary with metadata.

        """
        response = self._new_notifications(**kwargs)
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}
