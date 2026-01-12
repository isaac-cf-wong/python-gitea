"""Unit tests for BaseUser class."""

import pytest

from gitea.user.base import BaseUser


class TestBaseUser:
    """Test cases for BaseUser class."""

    @pytest.fixture
    def base_user(self):
        """Fixture to create a BaseUser instance."""
        return BaseUser()

    def test_build_get_workflow_jobs_params_required_only(self, base_user):
        """Test building params with only required status."""
        params = base_user._build_get_workflow_jobs_params(status="success")
        expected = {"status": "success"}
        assert params == expected

    def test_build_get_workflow_jobs_params_with_page(self, base_user):
        """Test building params with status and page."""
        params = base_user._build_get_workflow_jobs_params(status="failure", page=2)
        expected = {"status": "failure", "page": "2"}
        assert params == expected

    def test_build_get_workflow_jobs_params_with_limit(self, base_user):
        """Test building params with status and limit."""
        params = base_user._build_get_workflow_jobs_params(status="pending", limit=50)
        expected = {"status": "pending", "limit": "50"}
        assert params == expected

    def test_build_get_workflow_jobs_params_all_params(self, base_user):
        """Test building params with all parameters."""
        params = base_user._build_get_workflow_jobs_params(status="success", page=1, limit=10)
        expected = {"status": "success", "page": "1", "limit": "10"}
        assert params == expected

    def test_build_get_workflow_runs_params_empty(self, base_user):
        """Test building params with no parameters."""
        params = base_user._build_get_workflow_runs_params()
        expected = {}
        assert params == expected

    def test_build_get_workflow_runs_params_event(self, base_user):
        """Test building params with event."""
        params = base_user._build_get_workflow_runs_params(event="push")
        expected = {"event": "push"}
        assert params == expected

    def test_build_get_workflow_runs_params_branch(self, base_user):
        """Test building params with branch."""
        params = base_user._build_get_workflow_runs_params(branch="main")
        expected = {"branch": "main"}
        assert params == expected

    def test_build_get_workflow_runs_params_status(self, base_user):
        """Test building params with status."""
        params = base_user._build_get_workflow_runs_params(status="success")
        expected = {"status": "success"}
        assert params == expected

    def test_build_get_workflow_runs_params_actor(self, base_user):
        """Test building params with actor."""
        params = base_user._build_get_workflow_runs_params(actor="testuser")
        expected = {"actor": "testuser"}
        assert params == expected

    def test_build_get_workflow_runs_params_head_sha(self, base_user):
        """Test building params with head_sha."""
        params = base_user._build_get_workflow_runs_params(head_sha="abc123")
        expected = {"head_sha": "abc123"}
        assert params == expected

    def test_build_get_workflow_runs_params_page(self, base_user):
        """Test building params with page."""
        params = base_user._build_get_workflow_runs_params(page=3)
        expected = {"page": "3"}
        assert params == expected

    def test_build_get_workflow_runs_params_limit(self, base_user):
        """Test building params with limit."""
        params = base_user._build_get_workflow_runs_params(limit=25)
        expected = {"limit": "25"}
        assert params == expected

    def test_build_get_workflow_runs_params_all_params(self, base_user):
        """Test building params with all parameters."""
        params = base_user._build_get_workflow_runs_params(
            event="push", branch="main", status="success", actor="testuser", head_sha="abc123", page=1, limit=10
        )
        expected = {
            "event": "push",
            "branch": "main",
            "status": "success",
            "actor": "testuser",
            "head_sha": "abc123",
            "page": "1",
            "limit": "10",
        }
        assert params == expected
