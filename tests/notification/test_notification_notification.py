"""Unit tests for the Notification class."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gitea.notification.async_notification import AsyncNotification
from gitea.notification.notification import Notification


class TestNotification:
    """Test cases for the Notification class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture to create a mock Gitea client."""
        return MagicMock()

    @pytest.fixture
    def notification(self, mock_client):
        """Fixture to create a Notification instance."""
        return Notification(client=mock_client)

    def test_list_notifications(self, notification, mock_client):
        """Test list_notifications."""
        with patch("gitea.notification.notification.process_response") as mock_process:
            mock_process.return_value = ([{"id": 1, "unread": True}], 200)
            result = notification.list_notifications(all_notifications=True, page=1, limit=10)
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/notifications",
                params={"all": True, "page": 1, "limit": 10},
            )
            assert result == ([{"id": 1, "unread": True}], {"status_code": 200})

    def test_list_repo_notifications(self, notification, mock_client):
        """Test list_repo_notifications."""
        with patch("gitea.notification.notification.process_response") as mock_process:
            mock_process.return_value = ([{"id": 2}], 200)
            result = notification.list_repo_notifications(owner="o", repository="r")
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/repos/o/r/notifications",
                params={},
            )
            assert result == ([{"id": 2}], {"status_code": 200})

    def test_read_notifications(self, notification, mock_client):
        """Test read_notifications."""
        with patch("gitea.notification.notification.process_response") as mock_process:
            mock_process.return_value = ([{"id": 1}, {"id": 2}], 205)
            result = notification.read_notifications(all_notifications=True)
            mock_client._request.assert_called_once_with(
                method="PUT",
                endpoint="/notifications",
                params={"all": True},
            )
            assert result == ([{"id": 1}, {"id": 2}], {"status_code": 205})

    def test_read_notifications_empty(self, notification, mock_client):
        """Test read_notifications with an empty 205 response."""
        with patch("gitea.notification.notification.process_response") as mock_process:
            mock_process.return_value = ([], 205)
            result = notification.read_notifications(all_notifications=True)
            mock_client._request.assert_called_once_with(
                method="PUT",
                endpoint="/notifications",
                params={"all": True},
            )
            assert result == ([], {"status_code": 205})

    def test_read_repo_notifications(self, notification, mock_client):
        """Test read_repo_notifications."""
        with patch("gitea.notification.notification.process_response") as mock_process:
            mock_process.return_value = ([{"id": 3}], 205)
            result = notification.read_repo_notifications(owner="o", repository="r", to_status="read")
            mock_client._request.assert_called_once_with(
                method="PUT",
                endpoint="/repos/o/r/notifications",
                params={"to-status": "read"},
            )
            assert result == ([{"id": 3}], {"status_code": 205})

    def test_get_notification_thread(self, notification, mock_client):
        """Test get_notification_thread."""
        with patch("gitea.notification.notification.process_response") as mock_process:
            mock_process.return_value = ({"id": 42, "unread": True}, 200)
            result = notification.get_notification_thread(thread_id=42)
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/notifications/threads/42",
                params={},
            )
            assert result == ({"id": 42, "unread": True}, {"status_code": 200})

    def test_read_notification_thread(self, notification, mock_client):
        """Test read_notification_thread."""
        with patch("gitea.notification.notification.process_response") as mock_process:
            mock_process.return_value = ({"id": 42, "unread": False}, 200)
            result = notification.read_notification_thread(thread_id=42, to_status="read")
            mock_client._request.assert_called_once_with(
                method="PATCH",
                endpoint="/notifications/threads/42",
                params={"to-status": "read"},
            )
            assert result == ({"id": 42, "unread": False}, {"status_code": 200})

    def test_new_notifications(self, notification, mock_client):
        """Test new_notifications."""
        with patch("gitea.notification.notification.process_response") as mock_process:
            mock_process.return_value = ({"new": 3}, 200)
            result = notification.new_notifications()
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/notifications/new",
            )
            assert result == ({"new": 3}, {"status_code": 200})

    def test_list_notifications_with_datetime(self, notification, mock_client):
        """Test list_notifications with since/before datetime params."""
        since = datetime(2024, 1, 1, 12, 30)
        with patch("gitea.notification.notification.process_response") as mock_process:
            mock_process.return_value = ([], 200)
            result = notification.list_notifications(since=since)
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/notifications",
                params={"since": "2024-01-01T12:30:00"},
            )
            assert result == ([], {"status_code": 200})


class TestAsyncNotification:
    """Test cases for the AsyncNotification class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture to create a mock AsyncGitea client."""
        client = MagicMock()
        client._request = AsyncMock(return_value=MagicMock())
        return client

    @pytest.fixture
    def notification(self, mock_client):
        """Fixture to create an AsyncNotification instance."""
        return AsyncNotification(client=mock_client)

    @pytest.mark.asyncio
    async def test_list_notifications(self, notification, mock_client):
        """Test list_notifications (async)."""
        with patch("gitea.notification.async_notification.process_async_response") as mock_process:
            mock_process.return_value = ([{"id": 1, "unread": True}], 200)
            result = await notification.list_notifications(all_notifications=True)
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/notifications",
                params={"all": True},
            )
            assert result == ([{"id": 1, "unread": True}], {"status_code": 200})

    @pytest.mark.asyncio
    async def test_list_repo_notifications(self, notification, mock_client):
        """Test list_repo_notifications (async)."""
        with patch("gitea.notification.async_notification.process_async_response") as mock_process:
            mock_process.return_value = ([{"id": 2}], 200)
            result = await notification.list_repo_notifications(owner="o", repository="r")
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/repos/o/r/notifications",
                params={},
            )
            assert result == ([{"id": 2}], {"status_code": 200})

    @pytest.mark.asyncio
    async def test_read_notifications(self, notification, mock_client):
        """Test read_notifications (async)."""
        with patch("gitea.notification.async_notification.process_async_response") as mock_process:
            mock_process.return_value = ([{"id": 1}, {"id": 2}], 205)
            result = await notification.read_notifications(all_notifications=True)
            mock_client._request.assert_called_once_with(
                method="PUT",
                endpoint="/notifications",
                params={"all": True},
            )
            assert result == ([{"id": 1}, {"id": 2}], {"status_code": 205})

    @pytest.mark.asyncio
    async def test_read_notifications_empty(self, notification, mock_client):
        """Test read_notifications with an empty 205 response (async)."""
        with patch("gitea.notification.async_notification.process_async_response") as mock_process:
            mock_process.return_value = ([], 205)
            result = await notification.read_notifications(all_notifications=True)
            mock_client._request.assert_called_once_with(
                method="PUT",
                endpoint="/notifications",
                params={"all": True},
            )
            assert result == ([], {"status_code": 205})

    @pytest.mark.asyncio
    async def test_get_notification_thread(self, notification, mock_client):
        """Test get_notification_thread (async)."""
        with patch("gitea.notification.async_notification.process_async_response") as mock_process:
            mock_process.return_value = ({"id": 42}, 200)
            result = await notification.get_notification_thread(thread_id=42)
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/notifications/threads/42",
                params={},
            )
            assert result == ({"id": 42}, {"status_code": 200})

    @pytest.mark.asyncio
    async def test_read_notification_thread(self, notification, mock_client):
        """Test read_notification_thread (async)."""
        with patch("gitea.notification.async_notification.process_async_response") as mock_process:
            mock_process.return_value = ({"id": 42, "unread": False}, 200)
            result = await notification.read_notification_thread(thread_id=42, to_status="read")
            mock_client._request.assert_called_once_with(
                method="PATCH",
                endpoint="/notifications/threads/42",
                params={"to-status": "read"},
            )
            assert result == ({"id": 42, "unread": False}, {"status_code": 200})

    @pytest.mark.asyncio
    async def test_new_notifications(self, notification, mock_client):
        """Test new_notifications (async)."""
        with patch("gitea.notification.async_notification.process_async_response") as mock_process:
            mock_process.return_value = ({"new": 3}, 200)
            result = await notification.new_notifications()
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/notifications/new",
            )
            assert result == ({"new": 3}, {"status_code": 200})
