"""Unit tests for the BaseRepository class."""

import pytest

from gitea.repository.base import BaseRepository


class TestBaseRepository:
    """Test cases for the BaseRepository base class."""

    def test_list_repositories_endpoint_authenticated(self):
        """Test _list_repositories_endpoint for authenticated user."""
        base_repo = BaseRepository()
        endpoint = base_repo._list_repositories_endpoint(username=None, organization=None)
        assert endpoint == "/user/repos"

    def test_list_repositories_endpoint_by_username(self):
        """Test _list_repositories_endpoint for a specific user."""
        base_repo = BaseRepository()
        endpoint = base_repo._list_repositories_endpoint(username="testuser", organization=None)
        assert endpoint == "/users/testuser/repos"

    def test_list_repositories_endpoint_by_organization(self):
        """Test _list_repositories_endpoint for a specific organization."""
        base_repo = BaseRepository()
        endpoint = base_repo._list_repositories_endpoint(username=None, organization="test_org")
        assert endpoint == "/orgs/test_org/repos"

    def test_list_repositories_endpoint_both_raises_error(self):
        """Test _list_repositories_endpoint raises error when both username and organization are provided."""
        base_repo = BaseRepository()
        with pytest.raises(ValueError, match=r"Either username or organization must be provided, not both."):
            base_repo._list_repositories_endpoint(username="testuser", organization="test_org")

    def test_list_repositories_helper_authenticated(self):
        """Test _list_repositories_helper for authenticated user."""
        base_repo = BaseRepository()
        endpoint, params = base_repo._list_repositories_helper(username=None, organization=None)
        assert endpoint == "/user/repos"
        assert params == {}

    def test_list_repositories_helper_with_pagination(self):
        """Test _list_repositories_helper with pagination parameters."""
        base_repo = BaseRepository()
        endpoint, params = base_repo._list_repositories_helper(username=None, organization=None, page=2, limit=50)
        assert endpoint == "/user/repos"
        assert params == {"page": 2, "limit": 50}

    def test_list_repositories_helper_by_username(self):
        """Test _list_repositories_helper for a specific user."""
        base_repo = BaseRepository()
        endpoint, params = base_repo._list_repositories_helper(username="testuser", organization=None)
        assert endpoint == "/users/testuser/repos"
        assert params == {}

    def test_list_repositories_helper_by_username_with_pagination(self):
        """Test _list_repositories_helper for a specific user with pagination."""
        base_repo = BaseRepository()
        endpoint, params = base_repo._list_repositories_helper(username="testuser", organization=None, page=1, limit=20)
        assert endpoint == "/users/testuser/repos"
        assert params == {"page": 1, "limit": 20}

    def test_list_repositories_helper_by_organization(self):
        """Test _list_repositories_helper for a specific organization."""
        base_repo = BaseRepository()
        endpoint, params = base_repo._list_repositories_helper(username=None, organization="test_org")
        assert endpoint == "/orgs/test_org/repos"
        assert params == {}

    def test_list_repositories_helper_by_organization_with_pagination(self):
        """Test _list_repositories_helper for a specific organization with pagination."""
        base_repo = BaseRepository()
        endpoint, params = base_repo._list_repositories_helper(
            username=None, organization="test_org", page=3, limit=100
        )
        assert endpoint == "/orgs/test_org/repos"
        assert params == {"page": 3, "limit": 100}

    def test_list_repositories_helper_page_only(self):
        """Test _list_repositories_helper with only page parameter."""
        base_repo = BaseRepository()
        endpoint, params = base_repo._list_repositories_helper(username=None, organization=None, page=5)
        assert endpoint == "/user/repos"
        assert params == {"page": 5}

    def test_list_repositories_helper_limit_only(self):
        """Test _list_repositories_helper with only limit parameter."""
        base_repo = BaseRepository()
        endpoint, params = base_repo._list_repositories_helper(username=None, organization=None, limit=75)
        assert endpoint == "/user/repos"
        assert params == {"limit": 75}
