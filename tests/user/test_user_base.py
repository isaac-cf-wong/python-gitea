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

    def test_get_user_helper_merges_headers(self):
        """Headers passed in kwargs should be merged with default headers."""
        base_user = BaseUser()
        endpoint, kwargs = base_user._get_user_helper(username=None, headers={"Accept": "application/json"})
        assert endpoint == "/user"
        assert kwargs["headers"] == {"Content-Type": "application/json", "Accept": "application/json"}

    def test_get_user_helper_override_content_type(self):
        """Provided Content-Type should override the default."""
        base_user = BaseUser()
        endpoint, kwargs = base_user._get_user_helper(username="bob", headers={"Content-Type": "application/xml"})
        assert endpoint == "/users/bob"
        assert kwargs["headers"]["Content-Type"] == "application/xml"

    def test_update_user_settings_helper_all_none(self):
        """When no parameters are provided payload should be empty and headers set."""
        base_user = BaseUser()
        endpoint, payload, kwargs = base_user._update_user_settings_helper()
        assert endpoint == "/user/settings"
        assert payload == {}
        assert kwargs["headers"] == {"Content-Type": "application/json"}

    def test_update_user_settings_helper_all_params_and_headers(self):
        """All parameters should appear in payload and headers should include provided ones."""
        base_user = BaseUser()
        endpoint, payload, kwargs = base_user._update_user_settings_helper(
            diff_view_style="unified",
            full_name="Dev",
            hide_activity=True,
            hide_email=False,
            language="en",
            location="Earth",
            theme="light",
            website="https://example.com",
            headers={"Authorization": "token"},
        )
        assert endpoint == "/user/settings"
        assert payload == {
            "diff_view_style": "unified",
            "full_name": "Dev",
            "hide_activity": True,
            "hide_email": False,
            "language": "en",
            "location": "Earth",
            "theme": "light",
            "website": "https://example.com",
        }
        assert kwargs["headers"]["Content-Type"] == "application/json"
        assert kwargs["headers"]["Authorization"] == "token"

    def test_update_user_settings_helper_header_override(self):
        """Headers passed to update settings should be able to override defaults."""
        base_user = BaseUser()
        _endpoint, _payload, kwargs = base_user._update_user_settings_helper(
            headers={"Content-Type": "application/xml"}
        )
        assert kwargs["headers"]["Content-Type"] == "application/xml"
