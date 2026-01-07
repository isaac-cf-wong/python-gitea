"""Unit tests for the synchronous Gitea client."""

from unittest.mock import Mock, patch

import pytest

from gitea.client.gitea import Gitea


class TestGitea:
    """Test cases for the Gitea synchronous client."""

    @pytest.fixture
    def client(self):
        """Fixture to create a Gitea instance."""
        return Gitea(token="test_token", base_url="https://gitea.example.com")

    def test_init(self, client):
        """Test Gitea initialization."""
        assert client.token == "test_token"
        assert client.base_url == "https://gitea.example.com"
        assert isinstance(client.session, type(Mock())) is False  # Ensure it's a real requests.Session
        assert client.headers == {"Authorization": "token test_token"}

    @patch("requests.Session.request")
    def test_request_success(self, mock_request, client):
        """Test successful _request method."""
        # Mock the response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"key": "value"}
        mock_request.return_value = mock_response

        # Call the method
        result = client._request("GET", "users/testuser")

        # Assertions
        mock_request.assert_called_once_with(
            "GET",
            "https://gitea.example.com/api/v1/users/testuser",
            headers={"Authorization": "token test_token"},
            timeout=30,
        )
        assert result == {"key": "value"}

    @patch("requests.Session.request")
    def test_request_with_custom_headers(self, mock_request, client):
        """Test _request with custom headers."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"data": "test"}
        mock_request.return_value = mock_response

        result = client._request(
            "POST", "repos/test/repo/issues", headers={"Content-Type": "application/json"}, data={"title": "Test"}
        )

        mock_request.assert_called_once_with(
            "POST",
            "https://gitea.example.com/api/v1/repos/test/repo/issues",
            headers={"Authorization": "token test_token", "Content-Type": "application/json"},
            timeout=30,
            data={"title": "Test"},
        )
        assert result == {"data": "test"}

    @patch("requests.Session.request")
    def test_request_with_custom_timeout(self, mock_request, client):
        """Test _request with custom timeout."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response

        result = client._request("GET", "users", timeout=60)

        mock_request.assert_called_once_with(
            "GET", "https://gitea.example.com/api/v1/users", headers={"Authorization": "token test_token"}, timeout=60
        )
        assert result == {}

    @patch("requests.Session.request")
    def test_request_http_error(self, mock_request, client):
        """Test _request raises exception on HTTP error."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("404 Client Error")
        mock_request.return_value = mock_response

        with pytest.raises(Exception, match="404 Client Error"):
            client._request("GET", "nonexistent")
