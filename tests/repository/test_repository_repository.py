"""Unit tests for the Repository class."""

from unittest.mock import MagicMock, patch

import pytest

from gitea.repository.repository import Repository


class TestRepository:
    """Test cases for the Repository class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture to create a mock Gitea client."""
        client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": 1, "name": "repo1"}]
        mock_response.status_code = 200
        client._request.return_value = mock_response
        return client

    @pytest.fixture
    def repository(self, mock_client):
        """Fixture to create a Repository instance."""
        return Repository(client=mock_client)

    def test_list_repositories_authenticated(self, repository, mock_client):
        """Test list_repositories for authenticated user."""
        with patch("gitea.repository.repository.process_response") as mock_process:
            mock_process.return_value = ([{"id": 1, "name": "repo1"}], 200)
            result = repository.list_repositories()
            mock_client._request.assert_called_once_with(method="GET", endpoint="/user/repos", params={})
            assert result == ([{"id": 1, "name": "repo1"}], 200)

    def test_list_repositories_by_username(self, repository, mock_client):
        """Test list_repositories for a specific user."""
        with patch("gitea.repository.repository.process_response") as mock_process:
            mock_process.return_value = ([{"id": 2, "name": "other_repo"}], 200)
            result = repository.list_repositories(username="testuser")
            mock_client._request.assert_called_once_with(method="GET", endpoint="/users/testuser/repos", params={})
            assert result == ([{"id": 2, "name": "other_repo"}], 200)

    def test_list_repositories_by_organization(self, repository, mock_client):
        """Test list_repositories for a specific organization."""
        with patch("gitea.repository.repository.process_response") as mock_process:
            mock_process.return_value = (
                [{"id": 3, "name": "org_repo1"}, {"id": 4, "name": "org_repo2"}],
                200,
            )
            result = repository.list_repositories(organization="test_org")
            mock_client._request.assert_called_once_with(method="GET", endpoint="/orgs/test_org/repos", params={})
            assert result == (
                [{"id": 3, "name": "org_repo1"}, {"id": 4, "name": "org_repo2"}],
                200,
            )

    def test_list_repositories_with_pagination(self, repository, mock_client):
        """Test list_repositories with pagination parameters."""
        with patch("gitea.repository.repository.process_response") as mock_process:
            mock_process.return_value = ([{"id": 1, "name": "repo1"}], 200)
            result = repository.list_repositories(page=2, limit=50)
            mock_client._request.assert_called_once_with(
                method="GET", endpoint="/user/repos", params={"page": 2, "limit": 50}
            )
            assert result == ([{"id": 1, "name": "repo1"}], 200)

    def test_list_repositories_by_username_with_pagination(self, repository, mock_client):
        """Test list_repositories for a user with pagination."""
        with patch("gitea.repository.repository.process_response") as mock_process:
            mock_process.return_value = ([{"id": 5, "name": "paginated_repo"}], 200)
            result = repository.list_repositories(username="testuser", page=1, limit=25)
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/users/testuser/repos",
                params={"page": 1, "limit": 25},
            )
            assert result == ([{"id": 5, "name": "paginated_repo"}], 200)

    def test_list_repositories_by_organization_with_pagination(self, repository, mock_client):
        """Test list_repositories for an organization with pagination."""
        with patch("gitea.repository.repository.process_response") as mock_process:
            mock_process.return_value = (
                [{"id": 6, "name": "org_paginated_repo"}],
                200,
            )
            result = repository.list_repositories(organization="test_org", page=3, limit=100)
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/orgs/test_org/repos",
                params={"page": 3, "limit": 100},
            )
            assert result == ([{"id": 6, "name": "org_paginated_repo"}], 200)

    def test_list_repositories_empty_result(self, repository, mock_client):
        """Test list_repositories with empty result."""
        with patch("gitea.repository.repository.process_response") as mock_process:
            mock_process.return_value = ([], 200)
            result = repository.list_repositories()
            mock_client._request.assert_called_once()
            assert result == ([], 200)

    def test_list_repositories_error_response(self, repository, mock_client):
        """Test list_repositories with error response."""
        with patch("gitea.repository.repository.process_response") as mock_process:
            mock_process.return_value = ({"error": "Not Found"}, 404)
            result = repository.list_repositories(username="nonexistent")
            mock_client._request.assert_called_once()
            assert result == ({"error": "Not Found"}, 404)

    def test_list_repositories_with_kwargs(self, repository, mock_client):
        """Test list_repositories passing additional kwargs to _get method."""
        with patch("gitea.repository.repository.process_response") as mock_process:
            mock_process.return_value = ([{"id": 1, "name": "repo1"}], 200)
            result = repository.list_repositories(headers={"Custom": "Header"})
            mock_client._request.assert_called_once_with(
                method="GET", endpoint="/user/repos", params={}, headers={"Custom": "Header"}
            )
            assert result == ([{"id": 1, "name": "repo1"}], 200)
