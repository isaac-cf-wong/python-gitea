"""Unit tests for the base Client class."""

import pytest

from gitea.client.base import Client


class TestClient:
    """Test cases for the Client base class."""

    @pytest.fixture
    def client(self):
        """Fixture to create a Client instance."""
        return Client(token="test_token", base_url="https://gitea.example.com")

    def test_init(self, client):
        """Test Client initialization."""
        assert client.token == "test_token"
        assert client.base_url == "https://gitea.example.com"
        assert client.headers == {"Authorization": "token test_token"}

    def test_init_base_url_trailing_slash(self):
        """Test that trailing slash is stripped from base_url."""
        client = Client(token="test_token", base_url="https://gitea.example.com/")
        assert client.base_url == "https://gitea.example.com"

    def test_api_url_property(self, client):
        """Test the api_url property."""
        assert client.api_url == "https://gitea.example.com/api/v1"

    def test_build_url_simple_endpoint(self, client):
        """Test _build_url with a simple endpoint."""
        url = client._build_url("users")
        assert url == "https://gitea.example.com/api/v1/users"

    def test_build_url_endpoint_with_leading_slash(self, client):
        """Test _build_url with an endpoint that has a leading slash."""
        url = client._build_url("/users")
        assert url == "https://gitea.example.com/api/v1/users"

    def test_build_url_complex_endpoint(self, client):
        """Test _build_url with a complex endpoint."""
        url = client._build_url("repos/owner/repo/issues")
        assert url == "https://gitea.example.com/api/v1/repos/owner/repo/issues"

    def test_build_url_empty_endpoint(self, client):
        """Test _build_url with an empty endpoint."""
        url = client._build_url("")
        assert url == "https://gitea.example.com/api/v1/"
