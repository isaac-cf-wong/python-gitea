"""Unit tests for the BaseMilestone class."""

from datetime import datetime

from gitea.milestone.base import BaseMilestone


class TestBaseMilestone:
    """Test cases for the BaseMilestone class."""

    def test_list_milestones_endpoint(self):
        """Test _list_milestones_endpoint."""
        base = BaseMilestone()
        assert base._list_milestones_endpoint("owner", "repo") == "/repos/owner/repo/milestones"

    def test_list_milestones_helper(self):
        """Test _list_milestones_helper builds params."""
        base = BaseMilestone()
        endpoint, params = base._list_milestones_helper("owner", "repo", state="open", name="v1", page=1, limit=10)
        assert endpoint == "/repos/owner/repo/milestones"
        assert params == {"state": "open", "name": "v1", "page": 1, "limit": 10}

    def test_create_milestone_helper(self):
        """Test _create_milestone_helper builds the payload."""
        base = BaseMilestone()
        due_on = datetime(2024, 12, 31)
        endpoint, payload = base._create_milestone_helper(
            "owner", "repo", title="v1.0", description="First release", due_on=due_on, state="open"
        )
        assert endpoint == "/repos/owner/repo/milestones"
        assert payload == {
            "title": "v1.0",
            "description": "First release",
            "due_on": "2024-12-31T00:00:00",
            "state": "open",
        }

    def test_create_milestone_helper_required_only(self):
        """Test _create_milestone_helper with only the required title."""
        base = BaseMilestone()
        _, payload = base._create_milestone_helper("owner", "repo", title="v1.0")
        assert payload == {"title": "v1.0"}
