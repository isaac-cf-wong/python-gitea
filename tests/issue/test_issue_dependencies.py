"""Unit tests for issue dependency methods."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gitea.issue.async_issue import AsyncIssue
from gitea.issue.issue import Issue


class TestIssueDependencies:
    """Test cases for issue dependency methods on the Issue class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture to create a mock Gitea client."""
        return MagicMock()

    @pytest.fixture
    def issue(self, mock_client):
        """Fixture to create an Issue instance."""
        return Issue(client=mock_client)

    def test_list_issue_dependencies(self, issue, mock_client):
        """Test list_issue_dependencies."""
        with patch("gitea.issue.issue.process_response") as mock_process:
            mock_process.return_value = ([{"id": 10, "title": "Blocker"}], 200)
            result = issue.list_issue_dependencies(
                owner="test_owner", repository="test_repo", index=5, page=1, limit=20
            )
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/repos/test_owner/test_repo/issues/5/dependencies",
                params={"page": 1, "limit": 20},
            )
            assert result == ([{"id": 10, "title": "Blocker"}], {"status_code": 200})

    def test_list_issue_dependencies_defaults(self, issue, mock_client):
        """Test list_issue_dependencies without pagination params."""
        with patch("gitea.issue.issue.process_response") as mock_process:
            mock_process.return_value = ([], 200)
            result = issue.list_issue_dependencies(owner="o", repository="r", index=3)
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/repos/o/r/issues/3/dependencies",
                params={},
            )
            assert result == ([], {"status_code": 200})

    def test_create_issue_dependency(self, issue, mock_client):
        """Test create_issue_dependency."""
        with patch("gitea.issue.issue.process_response") as mock_process:
            mock_process.return_value = ({"id": 5, "title": "Target"}, 201)
            result = issue.create_issue_dependency(
                owner="test_owner",
                repository="test_repo",
                index=5,
                dependency_owner="other",
                dependency_repository="other_repo",
                dependency_index=7,
            )
            mock_client._request.assert_called_once_with(
                method="POST",
                endpoint="/repos/test_owner/test_repo/issues/5/dependencies",
                json={"owner": "other", "repo": "other_repo", "index": 7},
            )
            assert result == ({"id": 5, "title": "Target"}, {"status_code": 201})

    def test_remove_issue_dependency(self, issue, mock_client):
        """Test remove_issue_dependency."""
        with patch("gitea.issue.issue.process_response") as mock_process:
            mock_process.return_value = ({"id": 5, "title": "Target"}, 200)
            result = issue.remove_issue_dependency(
                owner="test_owner",
                repository="test_repo",
                index=5,
                dependency_owner="other",
                dependency_repository="other_repo",
                dependency_index=7,
            )
            mock_client._request.assert_called_once_with(
                method="DELETE",
                endpoint="/repos/test_owner/test_repo/issues/5/dependencies",
                json={"owner": "other", "repo": "other_repo", "index": 7},
            )
            assert result == ({"id": 5, "title": "Target"}, {"status_code": 200})


class TestAsyncIssueDependencies:
    """Test cases for issue dependency methods on the AsyncIssue class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture to create a mock Gitea client."""
        client = MagicMock()
        client._request = AsyncMock(return_value=MagicMock())
        return client

    @pytest.fixture
    def issue(self, mock_client):
        """Fixture to create an AsyncIssue instance."""
        return AsyncIssue(client=mock_client)

    @pytest.mark.asyncio
    async def test_list_issue_dependencies(self, issue, mock_client):
        """Test list_issue_dependencies (async)."""
        with patch("gitea.issue.async_issue.process_async_response") as mock_process:
            mock_process.return_value = ([{"id": 10, "title": "Blocker"}], 200)
            result = await issue.list_issue_dependencies(
                owner="test_owner", repository="test_repo", index=5, page=1, limit=20
            )
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/repos/test_owner/test_repo/issues/5/dependencies",
                params={"page": 1, "limit": 20},
            )
            assert result == ([{"id": 10, "title": "Blocker"}], {"status_code": 200})

    @pytest.mark.asyncio
    async def test_create_issue_dependency(self, issue, mock_client):
        """Test create_issue_dependency (async)."""
        with patch("gitea.issue.async_issue.process_async_response") as mock_process:
            mock_process.return_value = ({"id": 5, "title": "Target"}, 201)
            result = await issue.create_issue_dependency(
                owner="test_owner",
                repository="test_repo",
                index=5,
                dependency_owner="other",
                dependency_repository="other_repo",
                dependency_index=7,
            )
            mock_client._request.assert_called_once_with(
                method="POST",
                endpoint="/repos/test_owner/test_repo/issues/5/dependencies",
                json={"owner": "other", "repo": "other_repo", "index": 7},
            )
            assert result == ({"id": 5, "title": "Target"}, {"status_code": 201})

    @pytest.mark.asyncio
    async def test_remove_issue_dependency(self, issue, mock_client):
        """Test remove_issue_dependency (async)."""
        with patch("gitea.issue.async_issue.process_async_response") as mock_process:
            mock_process.return_value = ({"id": 5, "title": "Target"}, 200)
            result = await issue.remove_issue_dependency(
                owner="test_owner",
                repository="test_repo",
                index=5,
                dependency_owner="other",
                dependency_repository="other_repo",
                dependency_index=7,
            )
            mock_client._request.assert_called_once_with(
                method="DELETE",
                endpoint="/repos/test_owner/test_repo/issues/5/dependencies",
                json={"owner": "other", "repo": "other_repo", "index": 7},
            )
            assert result == ({"id": 5, "title": "Target"}, {"status_code": 200})
