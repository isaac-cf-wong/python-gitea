"""Unit tests for the Comment class."""

from unittest.mock import MagicMock, patch

import pytest

from gitea.comment.comment import Comment


class TestComment:
    """Test cases for the Comment class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture to create a mock Gitea client."""
        client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 1, "body": "Test Comment"}
        mock_response.status_code = 200
        client._request.return_value = mock_response
        return client

    @pytest.fixture
    def comment(self, mock_client):
        """Fixture to create a Comment instance."""
        return Comment(client=mock_client)

    def test_list_comments(self, comment, mock_client):
        """Test list_comments."""
        with patch("gitea.comment.comment.process_response") as mock_process:
            mock_process.return_value = ([{"id": 1, "body": "Comment 1"}], 200)
            result = comment.list_comments(owner="test_owner", repository="test_repo", index=1)
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/repos/test_owner/test_repo/issues/1/comments",
                params={},
            )
            assert result == ([{"id": 1, "body": "Comment 1"}], {"status_code": 200})

    def test_list_comments_with_pagination(self, comment, mock_client):
        """Test list_comments with pagination parameters."""
        with patch("gitea.comment.comment.process_response") as mock_process:
            mock_process.return_value = ([], 200)
            comment.list_comments(owner="test_owner", repository="test_repo", index=1, page=2, limit=10)
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/repos/test_owner/test_repo/issues/1/comments",
                params={"page": 2, "limit": 10},
            )

    def test_create_comment(self, comment, mock_client):
        """Test create_comment."""
        with patch("gitea.comment.comment.process_response") as mock_process:
            mock_process.return_value = ({"id": 1, "body": "New Comment"}, 201)
            result = comment.create_comment(owner="test_owner", repository="test_repo", index=1, body="New Comment")
            mock_client._request.assert_called_once_with(
                method="POST",
                endpoint="/repos/test_owner/test_repo/issues/1/comments",
                json={"body": "New Comment"},
            )
            assert result == ({"id": 1, "body": "New Comment"}, {"status_code": 201})

    def test_edit_comment(self, comment, mock_client):
        """Test edit_comment."""
        with patch("gitea.comment.comment.process_response") as mock_process:
            mock_process.return_value = ({"id": 1, "body": "Updated"}, 200)
            result = comment.edit_comment(owner="test_owner", repository="test_repo", comment_id=1, body="Updated")
            mock_client._request.assert_called_once_with(
                method="PATCH",
                endpoint="/repos/test_owner/test_repo/issues/comments/1",
                json={"body": "Updated"},
            )
            assert result == ({"id": 1, "body": "Updated"}, {"status_code": 200})

    def test_delete_comment(self, comment, mock_client):
        """Test delete_comment."""
        with patch("gitea.comment.comment.process_response") as mock_process:
            mock_process.return_value = ({}, 204)
            result = comment.delete_comment(owner="test_owner", repository="test_repo", comment_id=1)
            mock_client._request.assert_called_once_with(
                method="DELETE",
                endpoint="/repos/test_owner/test_repo/issues/comments/1",
            )
            assert result == ({}, {"status_code": 204})
