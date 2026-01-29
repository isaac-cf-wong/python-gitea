"""Unit tests for the AsyncRepository class."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gitea.repository.async_repository import AsyncRepository


class TestAsyncRepository:
    """Test cases for the AsyncRepository class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture to create a mock AsyncGitea client."""
        client = MagicMock()
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value=[{"id": 1, "name": "repo1"}])
        mock_response.status = 200
        client._request = AsyncMock(return_value=mock_response)
        return client

    @pytest.fixture
    def async_repository(self, mock_client):
        """Fixture to create an AsyncRepository instance."""
        return AsyncRepository(client=mock_client)

    @pytest.mark.asyncio
    async def test_list_repositories_authenticated(self, async_repository, mock_client):
        """Test list_repositories for authenticated user."""
        with patch("gitea.repository.async_repository.process_async_response") as mock_process:
            mock_process.return_value = ([{"id": 1, "name": "repo1"}], 200)
            result = await async_repository.list_repositories()
            mock_client._request.assert_called_once_with(method="GET", endpoint="/user/repos", params={})
            assert result == ([{"id": 1, "name": "repo1"}], 200)

    @pytest.mark.asyncio
    async def test_list_repositories_by_username(self, async_repository, mock_client):
        """Test list_repositories for a specific user."""
        with patch("gitea.repository.async_repository.process_async_response") as mock_process:
            mock_process.return_value = ([{"id": 2, "name": "other_repo"}], 200)
            result = await async_repository.list_repositories(username="testuser")
            mock_client._request.assert_called_once_with(method="GET", endpoint="/users/testuser/repos", params={})
            assert result == ([{"id": 2, "name": "other_repo"}], 200)

    @pytest.mark.asyncio
    async def test_list_repositories_by_organization(self, async_repository, mock_client):
        """Test list_repositories for a specific organization."""
        with patch("gitea.repository.async_repository.process_async_response") as mock_process:
            mock_process.return_value = (
                [{"id": 3, "name": "org_repo1"}, {"id": 4, "name": "org_repo2"}],
                200,
            )
            result = await async_repository.list_repositories(organization="test_org")
            mock_client._request.assert_called_once_with(method="GET", endpoint="/orgs/test_org/repos", params={})
            assert result == (
                [{"id": 3, "name": "org_repo1"}, {"id": 4, "name": "org_repo2"}],
                200,
            )

    @pytest.mark.asyncio
    async def test_list_repositories_with_pagination(self, async_repository, mock_client):
        """Test list_repositories with pagination parameters."""
        with patch("gitea.repository.async_repository.process_async_response") as mock_process:
            mock_process.return_value = ([{"id": 1, "name": "repo1"}], 200)
            result = await async_repository.list_repositories(page=2, limit=50)
            mock_client._request.assert_called_once_with(
                method="GET", endpoint="/user/repos", params={"page": 2, "limit": 50}
            )
            assert result == ([{"id": 1, "name": "repo1"}], 200)

    @pytest.mark.asyncio
    async def test_list_repositories_by_username_with_pagination(self, async_repository, mock_client):
        """Test list_repositories for a user with pagination."""
        with patch("gitea.repository.async_repository.process_async_response") as mock_process:
            mock_process.return_value = ([{"id": 5, "name": "paginated_repo"}], 200)
            result = await async_repository.list_repositories(username="testuser", page=1, limit=25)
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/users/testuser/repos",
                params={"page": 1, "limit": 25},
            )
            assert result == ([{"id": 5, "name": "paginated_repo"}], 200)

    @pytest.mark.asyncio
    async def test_list_repositories_by_organization_with_pagination(self, async_repository, mock_client):
        """Test list_repositories for an organization with pagination."""
        with patch("gitea.repository.async_repository.process_async_response") as mock_process:
            mock_process.return_value = (
                [{"id": 6, "name": "org_paginated_repo"}],
                200,
            )
            result = await async_repository.list_repositories(organization="test_org", page=3, limit=100)
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/orgs/test_org/repos",
                params={"page": 3, "limit": 100},
            )
            assert result == ([{"id": 6, "name": "org_paginated_repo"}], 200)

    @pytest.mark.asyncio
    async def test_list_repositories_empty_result(self, async_repository, mock_client):
        """Test list_repositories with empty result."""
        with patch("gitea.repository.async_repository.process_async_response") as mock_process:
            mock_process.return_value = ([], 200)
            result = await async_repository.list_repositories()
            mock_client._request.assert_called_once()
            assert result == ([], 200)

    @pytest.mark.asyncio
    async def test_list_repositories_error_response(self, async_repository, mock_client):
        """Test list_repositories with error response."""
        with patch("gitea.repository.async_repository.process_async_response") as mock_process:
            mock_process.return_value = ({"error": "Not Found"}, 404)
            result = await async_repository.list_repositories(username="nonexistent")
            mock_client._request.assert_called_once()
            assert result == ({"error": "Not Found"}, 404)

    @pytest.mark.asyncio
    async def test_list_repositories_with_kwargs(self, async_repository, mock_client):
        """Test list_repositories passing additional kwargs to _get method."""
        with patch("gitea.repository.async_repository.process_async_response") as mock_process:
            mock_process.return_value = ([{"id": 1, "name": "repo1"}], 200)
            result = await async_repository.list_repositories(headers={"Custom": "Header"})
            mock_client._request.assert_called_once_with(
                method="GET", endpoint="/user/repos", params={}, headers={"Custom": "Header"}
            )
            assert result == ([{"id": 1, "name": "repo1"}], 200)
