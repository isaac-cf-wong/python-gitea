"""Unit tests for the Milestone class."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from gitea.milestone.milestone import Milestone


class TestMilestone:
    """Test cases for the Milestone class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture to create a mock Gitea client."""
        client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 1, "title": "v1.0"}
        mock_response.status_code = 200
        client._request.return_value = mock_response
        return client

    @pytest.fixture
    def milestone(self, mock_client):
        """Fixture to create a Milestone instance."""
        return Milestone(client=mock_client)

    def test_list_milestones(self, milestone, mock_client):
        """Test list_milestones."""
        with patch("gitea.milestone.milestone.process_response") as mock_process:
            mock_process.return_value = ([{"id": 1, "title": "v1.0"}], 200)
            result = milestone.list_milestones(owner="test_owner", repository="test_repo", state="open")
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/repos/test_owner/test_repo/milestones",
                params={"state": "open"},
            )
            assert result == ([{"id": 1, "title": "v1.0"}], {"status_code": 200})

    def test_create_milestone(self, milestone, mock_client):
        """Test create_milestone."""
        due_on = datetime(2024, 12, 31)
        with patch("gitea.milestone.milestone.process_response") as mock_process:
            mock_process.return_value = ({"id": 1, "title": "v1.0"}, 201)
            result = milestone.create_milestone(
                owner="test_owner",
                repository="test_repo",
                title="v1.0",
                description="First release",
                due_on=due_on,
            )
            mock_client._request.assert_called_once_with(
                method="POST",
                endpoint="/repos/test_owner/test_repo/milestones",
                json={"title": "v1.0", "description": "First release", "due_on": "2024-12-31T00:00:00"},
            )
            assert result == ({"id": 1, "title": "v1.0"}, {"status_code": 201})
