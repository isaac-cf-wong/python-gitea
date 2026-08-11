"""Unit tests for the Notification base class."""

from datetime import datetime

from gitea.notification.base import BaseNotification


class TestBaseNotification:
    """Test cases for the BaseNotification class."""

    def setup_method(self):
        """Set up a BaseNotification instance for each test."""
        self.base = BaseNotification()

    def test_list_notifications_endpoint(self):
        """Test the list notifications endpoint URL."""
        assert self.base._list_notifications_endpoint() == "/notifications"

    def test_list_repo_notifications_endpoint(self):
        """Test the list repo notifications endpoint URL."""
        assert self.base._list_repo_notifications_endpoint("owner", "repo") == "/repos/owner/repo/notifications"

    def test_get_notification_thread_endpoint(self):
        """Test the get notification thread endpoint URL."""
        assert self.base._get_notification_thread_endpoint(42) == "/notifications/threads/42"

    def test_new_notifications_endpoint(self):
        """Test the new notifications endpoint URL."""
        assert self.base._new_notifications_endpoint() == "/notifications/new"

    def test_list_notifications_helper(self):
        """Test the list notifications helper."""
        since = datetime(2024, 1, 1, 12, 0)
        endpoint, params = self.base._list_notifications_helper(
            all_notifications=True, status_types=["unread"], since=since, page=2, limit=10
        )
        assert endpoint == "/notifications"
        assert params == {
            "all": True,
            "status-types": ["unread"],
            "since": "2024-01-01T12:00:00",
            "page": 2,
            "limit": 10,
        }

    def test_read_notifications_helper(self):
        """Test the read notifications helper."""
        endpoint, params = self.base._read_notifications_helper(all_notifications=True, to_status="read")
        assert endpoint == "/notifications"
        assert params == {"all": True, "to-status": "read"}

    def test_read_notification_thread_helper(self):
        """Test the read notification thread helper."""
        endpoint, params = self.base._read_notification_thread_helper(42, to_status="read")
        assert endpoint == "/notifications/threads/42"
        assert params == {"to-status": "read"}
