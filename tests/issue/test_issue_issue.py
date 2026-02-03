"""Unit tests for the Issue class."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from gitea.issue.issue import Issue


class TestIssue:
    """Test cases for the Issue class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture to create a mock Gitea client."""
        client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 1, "title": "Test Issue"}
        mock_response.status_code = 200
        client._request.return_value = mock_response
        return client

    @pytest.fixture
    def issue(self, mock_client):
        """Fixture to create an Issue instance."""
        return Issue(client=mock_client)

    def test_list_issues(self, issue, mock_client):
        """Test list_issues."""
        with patch("gitea.issue.issue.process_response") as mock_process:
            mock_process.return_value = ([{"id": 1, "title": "Issue 1"}], 200)
            result = issue.list_issues(owner="test_owner", repository="test_repo", state="open")
            expected_params = {"state": "open"}
            mock_client._request.assert_called_once_with(
                method="GET", endpoint="/repos/test_owner/test_repo/issues", params=expected_params
            )
            assert result == ([{"id": 1, "title": "Issue 1"}], {"status_code": 200})

    def test_get_issue(self, issue, mock_client):
        """Test get_issue."""
        with patch("gitea.issue.issue.process_response") as mock_process:
            mock_process.return_value = ({"id": 123, "title": "Test Issue"}, 200)
            result = issue.get_issue(owner="test_owner", repository="test_repo", index=123)
            mock_client._request.assert_called_once_with(
                method="GET", endpoint="/repos/test_owner/test_repo/issues/123"
            )
            assert result == ({"id": 123, "title": "Test Issue"}, {"status_code": 200})

    def test_edit_issue(self, issue, mock_client):
        """Test edit_issue."""
        due_date = datetime(2023, 6, 15)
        with patch("gitea.issue.issue.process_response") as mock_process:
            mock_process.return_value = ({"id": 123, "title": "Updated Title"}, 200)
            result = issue.edit_issue(
                owner="test_owner", repository="test_repo", index=123, title="Updated Title", due_date=due_date
            )
            expected_payload = {"title": "Updated Title", "due_date": "2023-06-15T00:00:00"}
            mock_client._request.assert_called_once_with(
                method="PATCH", endpoint="/repos/test_owner/test_repo/issues/123", json=expected_payload
            )
            assert result == ({"id": 123, "title": "Updated Title"}, {"status_code": 200})
