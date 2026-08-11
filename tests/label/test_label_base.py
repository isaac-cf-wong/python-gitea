"""Unit tests for the BaseLabel class."""

from gitea.label.base import BaseLabel


class TestBaseLabel:
    """Test cases for the BaseLabel class."""

    def test_list_labels_endpoint(self):
        """Test _list_labels_endpoint."""
        base = BaseLabel()
        assert base._list_labels_endpoint("owner", "repo") == "/repos/owner/repo/labels"

    def test_list_labels_helper(self):
        """Test _list_labels_helper builds params."""
        base = BaseLabel()
        endpoint, params = base._list_labels_helper("owner", "repo", page=1, limit=20)
        assert endpoint == "/repos/owner/repo/labels"
        assert params == {"page": 1, "limit": 20}

    def test_create_label_helper(self):
        """Test _create_label_helper builds the payload."""
        base = BaseLabel()
        endpoint, payload = base._create_label_helper("owner", "repo", name="bug", color="#e11d21", description="A bug")
        assert endpoint == "/repos/owner/repo/labels"
        assert payload == {"name": "bug", "color": "#e11d21", "description": "A bug"}

    def test_create_label_helper_without_description(self):
        """Test _create_label_helper omits description when absent."""
        base = BaseLabel()
        _, payload = base._create_label_helper("owner", "repo", name="bug", color="#e11d21")
        assert payload == {"name": "bug", "color": "#e11d21"}

    def test_edit_label_helper(self):
        """Test _edit_label_helper builds the payload."""
        base = BaseLabel()
        endpoint, payload = base._edit_label_helper("owner", "repo", label_id=5, name="new-name")
        assert endpoint == "/repos/owner/repo/labels/5"
        assert payload == {"name": "new-name"}

    def test_delete_label_helper(self):
        """Test _delete_label_helper builds the endpoint."""
        base = BaseLabel()
        assert base._delete_label_helper("owner", "repo", 5) == "/repos/owner/repo/labels/5"
