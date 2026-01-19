"""Unit tests for the User class."""

from unittest.mock import MagicMock, patch

import pytest

from gitea.user.user import User


class TestUser:
    """Test cases for the User class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture to create a mock Gitea client."""
        client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"login": "testuser", "id": 1}
        mock_response.status_code = 200
        client._request.return_value = mock_response
        return client

    @pytest.fixture
    def user(self, mock_client):
        """Fixture to create a User instance."""
        return User(client=mock_client)

    def test_get_user_authenticated(self, user, mock_client):
        """Test get_user for authenticated user."""
        with patch("gitea.user.user.process_response") as mock_process:
            mock_process.return_value = ({"login": "testuser", "id": 1}, 200)
            result = user.get_user()
            mock_client._request.assert_called_once_with(
                method="GET", endpoint="/user", headers={"Content-Type": "application/json"}
            )
            assert result == ({"login": "testuser", "id": 1}, 200)

    def test_get_user_by_username(self, user, mock_client):
        """Test get_user for a specific user."""
        with patch("gitea.user.user.process_response") as mock_process:
            mock_process.return_value = ({"login": "other_user", "id": 2}, 200)
            result = user.get_user(username="other_user")
            mock_client._request.assert_called_once_with(
                method="GET", endpoint="/users/other_user", headers={"Content-Type": "application/json"}
            )
            assert result == ({"login": "other_user", "id": 2}, 200)

    def test_update_user_settings(self, user, mock_client):
        """Test update_user_settings."""
        with patch("gitea.user.user.process_response") as mock_process:
            mock_process.return_value = ({"full_name": "Test User", "theme": "dark"}, 200)
            result = user.update_user_settings(full_name="Test User", theme="dark")
            expected_payload = {"full_name": "Test User", "theme": "dark"}
            mock_client._request.assert_called_once_with(
                method="PATCH",
                endpoint="/user/settings",
                json=expected_payload,
                headers={"Content-Type": "application/json"},
            )
            assert result == ({"full_name": "Test User", "theme": "dark"}, 200)
