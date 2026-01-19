"""Unit tests for the Resource base class."""

from unittest.mock import MagicMock

import pytest

from gitea.resource.resource import Resource


class TestResource:
    """Test cases for the Resource base class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture to create a mock Gitea client."""
        client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "test"}
        client._request = MagicMock(return_value=mock_response)
        return client

    @pytest.fixture
    def resource(self, mock_client):
        """Fixture to create a Resource instance."""
        return Resource(client=mock_client)

    def test_get(self, resource, mock_client):
        """Test the _get method."""
        mock_client._request.return_value.json.return_value = {"data": "test"}

        result = resource._get("users/testuser", timeout=30)

        mock_client._request.assert_called_once_with(method="GET", endpoint="users/testuser", timeout=30)
        assert result.json() == {"data": "test"}

    def test_post(self, resource, mock_client):
        """Test the _post method."""
        mock_client._request.return_value.json.return_value = {"id": 1}

        result = resource._post("repos/test/repo/issues", json={"title": "Test"})

        mock_client._request.assert_called_once_with(
            method="POST", endpoint="repos/test/repo/issues", json={"title": "Test"}
        )
        assert result.json() == {"id": 1}

    def test_put(self, resource, mock_client):
        """Test the _put method."""
        mock_client._request.return_value.json.return_value = {"updated": True}

        result = resource._put("user/settings", data={"name": "New Name"})

        mock_client._request.assert_called_once_with(method="PUT", endpoint="user/settings", data={"name": "New Name"})
        assert result.json() == {"updated": True}

    def test_delete(self, resource, mock_client):
        """Test the _delete method."""
        mock_client._request.return_value.json.return_value = {"deleted": True}

        result = resource._delete("repos/test/repo/issues/1")

        mock_client._request.assert_called_once_with(method="DELETE", endpoint="repos/test/repo/issues/1")
        assert result.json() == {"deleted": True}
