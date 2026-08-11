"""Unit tests for the AsyncComment class."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gitea.comment.async_comment import AsyncComment


class TestAsyncComment:
    """Test cases for the AsyncComment class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture to create a mock AsyncGitea client."""
        client = MagicMock()
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value={"id": 1, "body": "Test Comment"})
        mock_response.status = 200
        client._request = AsyncMock(return_value=mock_response)
        return client

    @pytest.fixture
    def async_comment(self, mock_client):
        """Fixture to create an AsyncComment instance."""
        return AsyncComment(client=mock_client)

    @pytest.mark.asyncio
    async def test_list_comments(self, async_comment, mock_client):
        """Test list_comments."""
        with patch("gitea.comment.async_comment.process_async_response") as mock_process:
            mock_process.return_value = ([{"id": 1, "body": "Comment 1"}], 200)
            result = await async_comment.list_comments(owner="test_owner", repository="test_repo", index=1)
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/repos/test_owner/test_repo/issues/1/comments",
                params={},
            )
            assert result == ([{"id": 1, "body": "Comment 1"}], {"status_code": 200})

    @pytest.mark.asyncio
    async def test_create_comment(self, async_comment, mock_client):
        """Test create_comment."""
        with patch("gitea.comment.async_comment.process_async_response") as mock_process:
            mock_process.return_value = ({"id": 1, "body": "New Comment"}, 201)
            result = await async_comment.create_comment(
                owner="test_owner", repository="test_repo", index=1, body="New Comment"
            )
            mock_client._request.assert_called_once_with(
                method="POST",
                endpoint="/repos/test_owner/test_repo/issues/1/comments",
                json={"body": "New Comment"},
            )
            assert result == ({"id": 1, "body": "New Comment"}, {"status_code": 201})

    @pytest.mark.asyncio
    async def test_edit_comment(self, async_comment, mock_client):
        """Test edit_comment."""
        with patch("gitea.comment.async_comment.process_async_response") as mock_process:
            mock_process.return_value = ({"id": 1, "body": "Updated"}, 200)
            result = await async_comment.edit_comment(
                owner="test_owner", repository="test_repo", comment_id=1, body="Updated"
            )
            mock_client._request.assert_called_once_with(
                method="PATCH",
                endpoint="/repos/test_owner/test_repo/issues/comments/1",
                json={"body": "Updated"},
            )
            assert result == ({"id": 1, "body": "Updated"}, {"status_code": 200})

    @pytest.mark.asyncio
    async def test_delete_comment(self, async_comment, mock_client):
        """Test delete_comment."""
        with patch("gitea.comment.async_comment.process_async_response") as mock_process:
            mock_process.return_value = ({}, 204)
            result = await async_comment.delete_comment(owner="test_owner", repository="test_repo", comment_id=1)
            mock_client._request.assert_called_once_with(
                method="DELETE",
                endpoint="/repos/test_owner/test_repo/issues/comments/1",
            )
            assert result == ({}, {"status_code": 204})
