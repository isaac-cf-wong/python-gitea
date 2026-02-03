"""Unit tests for the AsyncUser class."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gitea.user.async_user import AsyncUser


class TestAsyncUser:
    """Test cases for the AsyncUser class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture to create a mock AsyncGitea client."""
        client = MagicMock()
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value={"login": "testuser", "id": 1})
        mock_response.status = 200
        client._request = AsyncMock(return_value=mock_response)
        return client

    @pytest.fixture
    def async_user(self, mock_client):
        """Fixture to create an AsyncUser instance."""
        return AsyncUser(client=mock_client)

    @pytest.mark.asyncio
    async def test_get_user_authenticated(self, async_user, mock_client):
        """Test get_user for authenticated user."""
        with patch("gitea.user.async_user.process_async_response") as mock_process:
            mock_process.return_value = ({"login": "testuser", "id": 1}, 200)
            result = await async_user.get_user()
            mock_client._request.assert_called_once_with(
                method="GET", endpoint="/user", headers={"Content-Type": "application/json"}
            )
            assert result == ({"login": "testuser", "id": 1}, {"status_code": 200})

    @pytest.mark.asyncio
    async def test_get_user_by_username(self, async_user, mock_client):
        """Test get_user for a specific user."""
        with patch("gitea.user.async_user.process_async_response") as mock_process:
            mock_process.return_value = ({"login": "other_user", "id": 2}, 200)
            result = await async_user.get_user(username="other_user")
            mock_client._request.assert_called_once_with(
                method="GET", endpoint="/users/other_user", headers={"Content-Type": "application/json"}
            )
            assert result == ({"login": "other_user", "id": 2}, {"status_code": 200})

    @pytest.mark.asyncio
    async def test_update_user_settings(self, async_user, mock_client):
        """Test update_user_settings."""
        with patch("gitea.user.async_user.process_async_response") as mock_process:
            mock_process.return_value = ({"full_name": "Test User", "theme": "dark"}, 200)
            result = await async_user.update_user_settings(full_name="Test User", theme="dark")
            expected_payload = {"full_name": "Test User", "theme": "dark"}
            mock_client._request.assert_called_once_with(
                method="PATCH",
                endpoint="/user/settings",
                json=expected_payload,
                headers={"Content-Type": "application/json"},
            )
            assert result == ({"full_name": "Test User", "theme": "dark"}, {"status_code": 200})
