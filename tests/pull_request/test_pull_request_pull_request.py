"""Unit tests for the synchronous PullRequest class."""

from unittest.mock import MagicMock, patch

import pytest

from gitea.pull_request.pull_request import PullRequest


class TestPullRequest:
    """Test cases for the PullRequest synchronous class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture to create a mock Gitea client."""
        return MagicMock()

    @pytest.fixture
    def pull_request(self, mock_client):
        """Fixture to create a PullRequest instance."""
        return PullRequest(client=mock_client)

    def test_init(self, pull_request, mock_client):
        """Test PullRequest initialization."""
        assert pull_request.client == mock_client

    @patch("gitea.pull_request.pull_request.process_response")
    def test_list_pull_requests(self, mock_process_response, pull_request, mock_client):
        """Test list_pull_requests method."""
        # Mock the response
        mock_response = MagicMock()
        mock_client._request.return_value = mock_response
        mock_process_response.return_value = ([{"id": 1}], 200)

        result = pull_request.list_pull_requests("owner", "repo")

        # Verify _request was called correctly
        mock_client._request.assert_called_once_with(
            method="GET",
            endpoint="/repos/owner/repo/pulls",
            params={},
        )
        mock_process_response.assert_called_once_with(mock_response, default=[])
        assert result == ([{"id": 1}], {"status_code": 200})

    @patch("gitea.pull_request.pull_request.process_response")
    def test_list_pull_requests_with_params(self, mock_process_response, pull_request, mock_client):
        """Test list_pull_requests method with parameters."""
        # Mock the response
        mock_response = MagicMock()
        mock_client._request.return_value = mock_response
        mock_process_response.return_value = ([{"id": 1}], 200)

        result = pull_request.list_pull_requests(
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
        assert result == ([{"id": 1}], {"status_code": 200})

    @patch("gitea.pull_request.pull_request.process_response")
    def test_list_pull_requests_all_params(self, mock_process_response, pull_request, mock_client):
        """Test list_pull_requests method with all parameters."""
        # Mock the response
        mock_response = MagicMock()
        mock_client._request.return_value = mock_response
        mock_process_response.return_value = ([{"id": 1}], 200)

        result = pull_request.list_pull_requests(
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
        assert result == ([{"id": 1}], {"status_code": 200})
