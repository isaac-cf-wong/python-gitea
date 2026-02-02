"""Unit tests for the base PullRequest class."""

import pytest

from gitea.pull_request.base import BasePullRequest


class TestBasePullRequest:
    """Test cases for the BasePullRequest base class."""

    @pytest.fixture
    def base_pr(self):
        """Fixture to create a BasePullRequest instance."""
        return BasePullRequest()

    def test_list_pull_requests_endpoint(self, base_pr):
        """Test _list_pull_requests_endpoint constructs the correct URL."""
        endpoint = base_pr._list_pull_requests_endpoint("owner", "repo")
        assert endpoint == "/repos/owner/repo/pulls"

    def test_list_pull_requests_helper_no_params(self, base_pr):
        """Test _list_pull_requests_helper with no optional parameters."""
        endpoint, params = base_pr._list_pull_requests_helper("owner", "repo")
        assert endpoint == "/repos/owner/repo/pulls"
        assert params == {}

    def test_list_pull_requests_helper_with_params(self, base_pr):
        """Test _list_pull_requests_helper with all parameters."""
        endpoint, params = base_pr._list_pull_requests_helper(
            owner="owner",
            repository="repo",
            base_branch="main",
            state="open",
            sort="recentupdate",
            milestone=1,
            labels=[1, 2],
            poster="user",
            page=1,
            limit=10,
        )
        assert endpoint == "/repos/owner/repo/pulls"
        expected_params = {
            "base": "main",
            "state": "open",
            "sort": "recentupdate",
            "milestone": 1,
            "labels": [1, 2],
            "poster": "user",
            "page": 1,
            "limit": 10,
        }
        assert params == expected_params

    def test_list_pull_requests_helper_partial_params(self, base_pr):
        """Test _list_pull_requests_helper with some parameters."""
        endpoint, params = base_pr._list_pull_requests_helper(
            owner="owner",
            repository="repo",
            state="closed",
            page=2,
        )
        assert endpoint == "/repos/owner/repo/pulls"
        expected_params = {
            "state": "closed",
            "page": 2,
        }
        assert params == expected_params
