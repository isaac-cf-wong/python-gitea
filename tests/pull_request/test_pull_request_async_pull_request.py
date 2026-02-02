"""Unit tests for the asynchronous AsyncPullRequest class."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gitea.pull_request.async_pull_request import AsyncPullRequest


class TestAsyncPullRequest:
    """Test cases for the AsyncPullRequest asynchronous class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture to create a mock AsyncGitea client."""
        return MagicMock()

    @pytest.fixture
    def async_pull_request(self, mock_client):
        """Fixture to create an AsyncPullRequest instance."""
        return AsyncPullRequest(client=mock_client)

    def test_init(self, async_pull_request, mock_client):
        """Test AsyncPullRequest initialization."""
        assert async_pull_request.client == mock_client

    @pytest.mark.asyncio
    @patch("gitea.pull_request.async_pull_request.process_async_response", new_callable=AsyncMock)
    async def test_list_pull_requests(self, mock_process_response, async_pull_request, mock_client):
        """Test list_pull_requests method."""
        # Mock the response
        mock_response = MagicMock()
        mock_client._request = AsyncMock(return_value=mock_response)
        mock_process_response.return_value = ([{"id": 1}], 200)

        result = await async_pull_request.list_pull_requests("owner", "repo")

        # Verify _request was called correctly
        mock_client._request.assert_called_once_with(
            method="GET",
            endpoint="/repos/owner/repo/pulls",
            params={},
        )
        mock_process_response.assert_called_once_with(mock_response, default=[])
        assert result == ([{"id": 1}], 200)

    @pytest.mark.asyncio
    @patch("gitea.pull_request.async_pull_request.process_async_response", new_callable=AsyncMock)
    async def test_list_pull_requests_with_params(self, mock_process_response, async_pull_request, mock_client):
        """Test list_pull_requests method with parameters."""
        # Mock the response
        mock_response = MagicMock()
        mock_client._request = AsyncMock(return_value=mock_response)
        mock_process_response.return_value = ([{"id": 1}], 200)

        result = await async_pull_request.list_pull_requests(
            owner="owner",
            repository="repo",
            state="open",
            page=1,
            limit=10,
        )

        # Verify _request was called with correct params
        expected_params = {"state": "open", "page": 1, "limit": 10}
        mock_client._request.assert_called_once_with(
            method="GET",
            endpoint="/repos/owner/repo/pulls",
            params=expected_params,
        )
        mock_process_response.assert_called_once_with(mock_response, default=[])
        assert result == ([{"id": 1}], 200)

    @pytest.mark.asyncio
    @patch("gitea.pull_request.async_pull_request.process_async_response", new_callable=AsyncMock)
    async def test_list_pull_requests_all_params(self, mock_process_response, async_pull_request, mock_client):
        """Test list_pull_requests method with all parameters."""
        # Mock the response
        mock_response = MagicMock()
        mock_client._request = AsyncMock(return_value=mock_response)
        mock_process_response.return_value = ([{"id": 1}], 200)

        result = await async_pull_request.list_pull_requests(
            owner="owner",
            repository="repo",
            base_branch="main",
            state="closed",
            sort="recentupdate",
            milestone=1,
            labels=[1, 2],
            poster="user",
            page=1,
            limit=10,
        )

        # Verify _request was called with all params
        expected_params = {
            "base": "main",
            "state": "closed",
            "sort": "recentupdate",
            "milestone": 1,
            "labels": [1, 2],
            "poster": "user",
            "page": 1,
            "limit": 10,
        }
        mock_client._request.assert_called_once_with(
            method="GET",
            endpoint="/repos/owner/repo/pulls",
            params=expected_params,
        )
        mock_process_response.assert_called_once_with(mock_response, default=[])
        assert result == ([{"id": 1}], 200)
