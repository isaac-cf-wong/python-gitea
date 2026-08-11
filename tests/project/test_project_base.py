"""Unit tests for the Project base class."""

from gitea.project.base import BaseProject


class TestBaseProject:
    """Test cases for the BaseProject class."""

    def setup_method(self):
        """Set up a BaseProject instance for each test."""
        self.base = BaseProject()

    def test_list_projects_endpoint(self):
        """Test the list projects endpoint URL."""
        assert self.base._list_projects_endpoint("owner", "repo") == "/repos/owner/repo/projects"

    def test_get_project_endpoint(self):
        """Test the get project endpoint URL."""
        assert self.base._get_project_endpoint("owner", "repo", 7) == "/repos/owner/repo/projects/7"

    def test_list_project_columns_endpoint(self):
        """Test the list project columns endpoint URL."""
        assert self.base._list_project_columns_endpoint("owner", "repo", 7) == "/repos/owner/repo/projects/7/columns"

    def test_get_project_column_endpoint(self):
        """Test the get project column endpoint URL."""
        assert self.base._get_project_column_endpoint("owner", "repo", 7, 3) == "/repos/owner/repo/projects/7/columns/3"

    def test_list_project_column_issues_endpoint(self):
        """Test the list project column issues endpoint URL."""
        assert (
            self.base._list_project_column_issues_endpoint("owner", "repo", 7, 3)
            == "/repos/owner/repo/projects/7/columns/3/issues"
        )

    def test_create_project_helper(self):
        """Test the create project helper."""
        endpoint, payload = self.base._create_project_helper(
            "owner", "repo", "Board", description="desc", template_type="basic_kanban"
        )
        assert endpoint == "/repos/owner/repo/projects"
        assert payload == {"title": "Board", "description": "desc", "template_type": "basic_kanban"}

    def test_move_project_issue_helper(self):
        """Test the move project issue helper."""
        endpoint, payload = self.base._move_project_issue_helper("owner", "repo", 7, 100, 3, sorting=2)
        assert endpoint == "/repos/owner/repo/projects/7/issues/100/move"
        assert payload == {"column_id": 3, "sorting": 2}
