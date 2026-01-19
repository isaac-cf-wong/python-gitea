"""Unit tests for the BaseUser class."""

from gitea.user.base import BaseUser


class TestBaseUser:
    """Test cases for the BaseUser base class."""

    def test_get_user_endpoint_authenticated(self):
        """Test _get_user_endpoint for authenticated user."""
        base_user = BaseUser()
        endpoint = base_user._get_user_endpoint(username=None)
        assert endpoint == "/user"

    def test_get_user_endpoint_by_username(self):
        """Test _get_user_endpoint for a specific user."""
        base_user = BaseUser()
        endpoint = base_user._get_user_endpoint(username="testuser")
        assert endpoint == "/users/testuser"

    def test_get_user_helper_authenticated(self):
        """Test _get_user_helper for authenticated user."""
        base_user = BaseUser()
        endpoint, kwargs = base_user._get_user_helper(username=None)
        assert endpoint == "/user"
        assert kwargs["headers"] == {"Content-Type": "application/json"}

    def test_get_user_helper_by_username(self):
        """Test _get_user_helper for a specific user."""
        base_user = BaseUser()
        endpoint, kwargs = base_user._get_user_helper(username="testuser")
        assert endpoint == "/users/testuser"
        assert kwargs["headers"] == {"Content-Type": "application/json"}

    def test_update_user_settings_endpoint(self):
        """Test _update_user_settings_endpoint."""
        base_user = BaseUser()
        endpoint = base_user._update_user_settings_endpoint()
        assert endpoint == "/user/settings"

    def test_update_user_settings_helper(self):
        """Test _update_user_settings_helper with some parameters."""
        base_user = BaseUser()
        endpoint, payload, kwargs = base_user._update_user_settings_helper(
            full_name="Test User", theme="dark", location="Earth"
        )
        assert endpoint == "/user/settings"
        assert payload == {"full_name": "Test User", "theme": "dark", "location": "Earth"}
        assert kwargs["headers"] == {"Content-Type": "application/json"}
