"""Unit tests for the AsyncResource base class."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from gitea.resource.async_resource import AsyncResource


class TestAsyncResource:
    """Test cases for the AsyncResource base class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture to create a mock AsyncGitea client."""
        client = MagicMock()
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value={"data": "test"})
        client._request = AsyncMock(return_value=mock_response)
        return client

    @pytest.fixture
    def resource(self, mock_client):
        """Fixture to create an AsyncResource instance."""
        return AsyncResource(client=mock_client)

    @pytest.mark.asyncio
    async def test_get(self, resource, mock_client):
        """Test the _get method."""
        mock_client._request.return_value.json = AsyncMock(return_value={"data": "test"})

        result = await resource._get("users/testuser", timeout=30)

        mock_client._request.assert_called_once_with(method="GET", endpoint="users/testuser", timeout=30)
        assert await result.json() == {"data": "test"}

    @pytest.mark.asyncio
    async def test_post(self, resource, mock_client):
        """Test the _post method."""
        mock_client._request.return_value.json = AsyncMock(return_value={"id": 1})

        result = await resource._post("repos/test/repo/issues", json={"title": "Test"})

        mock_client._request.assert_called_once_with(
            method="POST", endpoint="repos/test/repo/issues", json={"title": "Test"}
        )
        assert await result.json() == {"id": 1}

    @pytest.mark.asyncio
    async def test_put(self, resource, mock_client):
        """Test the _put method."""
        mock_client._request.return_value.json = AsyncMock(return_value={"updated": True})

        result = await resource._put("user/settings", data={"name": "New Name"})

        mock_client._request.assert_called_once_with(method="PUT", endpoint="user/settings", data={"name": "New Name"})
        assert await result.json() == {"updated": True}

    @pytest.mark.asyncio
    async def test_delete(self, resource, mock_client):
        """Test the _delete method."""
        mock_client._request.return_value.json = AsyncMock(return_value={"deleted": True})

        result = await resource._delete("repos/test/repo/issues/1")

        mock_client._request.assert_called_once_with(method="DELETE", endpoint="repos/test/repo/issues/1")
        assert await result.json() == {"deleted": True}
