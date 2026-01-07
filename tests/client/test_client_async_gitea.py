"""Unit tests for the asynchronous AsyncGitea client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gitea.client.async_gitea import AsyncGitea


class TestAsyncGitea:
    """Test cases for the AsyncGitea asynchronous client."""

    @pytest.fixture
    def client(self):
        """Fixture to create an AsyncGitea instance."""
        return AsyncGitea(token="test_token", base_url="https://gitea.example.com")

    def test_init(self, client):
        """Test AsyncGitea initialization."""
        assert client.token == "test_token"
        assert client.base_url == "https://gitea.example.com"
        assert client.session is None
        assert client.headers == {"Authorization": "token test_token"}

    @pytest.mark.asyncio
    async def test_aenter(self, client):
        """Test entering the async context manager."""
        async_client = await client.__aenter__()
        assert async_client is client
        assert client.session is not None
        # Clean up
        await client.__aexit__(None, None, None)

    @pytest.mark.asyncio
    async def test_aexit(self, client):
        """Test exiting the async context manager."""
        await client.__aenter__()
        assert client.session is not None
        await client.__aexit__(None, None, None)
        assert client.session is None

    @patch("gitea.client.async_gitea.ClientSession")
    def test_get_session(self, mock_session_class, client):
        """Test _get_session creates a new session."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        session = client._get_session()
        mock_session_class.assert_called_once_with(headers=None)
        assert session is mock_session

    @pytest.mark.asyncio
    async def test_request_success(self, client):
        """Test successful _request method."""
        # Mock the session and response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json = AsyncMock(return_value={"key": "value"})

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.request.return_value = mock_cm

        with (
            patch("gitea.client.async_gitea.ClientTimeout") as mock_timeout_class,
            patch.object(client, "_get_session", return_value=mock_session),
        ):
            mock_timeout = MagicMock()
            mock_timeout_class.return_value = mock_timeout

            result = await client._request("GET", "users/testuser")

        mock_session.request.assert_called_once_with(
            method="GET",
            url="https://gitea.example.com/api/v1/users/testuser",
            headers={"Authorization": "token test_token"},
            timeout=mock_timeout,
        )
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_request_with_custom_headers(self, client):
        """Test _request with custom headers."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json = AsyncMock(return_value={"data": "test"})

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.request.return_value = mock_cm

        with (
            patch("gitea.client.async_gitea.ClientTimeout") as mock_timeout_class,
            patch.object(client, "_get_session", return_value=mock_session),
        ):
            mock_timeout = MagicMock()
            mock_timeout_class.return_value = mock_timeout

            result = await client._request(
                "POST", "repos/test/repo/issues", headers={"Content-Type": "application/json"}
            )

        expected_headers = {"Authorization": "token test_token", "Content-Type": "application/json"}
        mock_session.request.assert_called_once_with(
            method="POST",
            url="https://gitea.example.com/api/v1/repos/test/repo/issues",
            headers=expected_headers,
            timeout=mock_timeout,
        )
        assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_request_with_custom_timeout(self, client):
        """Test _request with custom timeout."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json = AsyncMock(return_value={})

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.request.return_value = mock_cm

        with (
            patch("aiohttp.ClientTimeout") as mock_timeout_class,
            patch.object(client, "_get_session", return_value=mock_session),
        ):
            mock_timeout = MagicMock()
            mock_timeout.total = 60
            mock_timeout_class.return_value = mock_timeout

            result = await client._request("GET", "users", timeout=60)

        # Check that timeout is passed
        call_args = mock_session.request.call_args
        assert call_args[1]["timeout"].total == 60
        assert result == {}

    @pytest.mark.asyncio
    async def test_request_http_error(self, client):
        """Test _request raises exception on HTTP error."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("404 Client Error")

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.request.return_value = mock_cm

        with (
            patch("gitea.client.async_gitea.ClientTimeout") as mock_timeout_class,
            patch.object(client, "_get_session", return_value=mock_session),
        ):
            mock_timeout = MagicMock()
            mock_timeout_class.return_value = mock_timeout

            with pytest.raises(Exception, match="404 Client Error"):
                await client._request("GET", "nonexistent")
