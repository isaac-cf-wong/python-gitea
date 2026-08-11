"""Unit tests for the AsyncMilestone class."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gitea.milestone.async_milestone import AsyncMilestone


class TestAsyncMilestone:
    """Test cases for the AsyncMilestone class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture to create a mock AsyncGitea client."""
        client = MagicMock()
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value={"id": 1, "title": "v1.0"})
        mock_response.status = 200
        client._request = AsyncMock(return_value=mock_response)
        return client

    @pytest.fixture
    def async_milestone(self, mock_client):
        """Fixture to create an AsyncMilestone instance."""
        return AsyncMilestone(client=mock_client)

    @pytest.mark.asyncio
    async def test_list_milestones(self, async_milestone, mock_client):
        """Test list_milestones."""
        with patch("gitea.milestone.async_milestone.process_async_response") as mock_process:
            mock_process.return_value = ([{"id": 1, "title": "v1.0"}], 200)
            result = await async_milestone.list_milestones(owner="test_owner", repository="test_repo")
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/repos/test_owner/test_repo/milestones",
                params={},
            )
            assert result == ([{"id": 1, "title": "v1.0"}], {"status_code": 200})

    @pytest.mark.asyncio
    async def test_create_milestone(self, async_milestone, mock_client):
        """Test create_milestone."""
        due_on = datetime(2024, 12, 31)
        with patch("gitea.milestone.async_milestone.process_async_response") as mock_process:
            mock_process.return_value = ({"id": 1, "title": "v1.0"}, 201)
            result = await async_milestone.create_milestone(
                owner="test_owner",
                repository="test_repo",
                title="v1.0",
                due_on=due_on,
            )
            mock_client._request.assert_called_once_with(
                method="POST",
                endpoint="/repos/test_owner/test_repo/milestones",
                json={"title": "v1.0", "due_on": "2024-12-31T00:00:00"},
            )
            assert result == ({"id": 1, "title": "v1.0"}, {"status_code": 201})
