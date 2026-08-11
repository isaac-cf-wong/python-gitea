"""Unit tests for the BaseComment class."""

from gitea.comment.base import BaseComment


class TestBaseComment:
    """Test cases for the BaseComment class."""

    def test_list_comments_endpoint(self):
        """Test _list_comments_endpoint."""
        base = BaseComment()
        assert base._list_comments_endpoint("owner", "repo", 7) == "/repos/owner/repo/issues/7/comments"

    def test_list_comments_helper(self):
        """Test _list_comments_helper builds params."""
        base = BaseComment()
        endpoint, params = base._list_comments_helper("owner", "repo", 7, page=2, limit=5)
        assert endpoint == "/repos/owner/repo/issues/7/comments"
        assert params == {"page": 2, "limit": 5}

    def test_create_comment_helper(self):
        """Test _create_comment_helper builds the payload."""
        base = BaseComment()
        endpoint, payload = base._create_comment_helper("owner", "repo", 7, body="Hello")
        assert endpoint == "/repos/owner/repo/issues/7/comments"
        assert payload == {"body": "Hello"}

    def test_edit_comment_helper(self):
        """Test _edit_comment_helper builds the payload."""
        base = BaseComment()
        endpoint, payload = base._edit_comment_helper("owner", "repo", 42, body="Updated")
        assert endpoint == "/repos/owner/repo/issues/comments/42"
        assert payload == {"body": "Updated"}

    def test_delete_comment_helper(self):
        """Test _delete_comment_helper builds the endpoint."""
        base = BaseComment()
        assert base._delete_comment_helper("owner", "repo", 42) == "/repos/owner/repo/issues/comments/42"
