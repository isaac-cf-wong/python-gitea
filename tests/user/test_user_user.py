"""Unit tests for User resource."""

from unittest.mock import MagicMock

import pytest

from gitea.user.user import User


class TestUser:
    """Test cases for User resource."""

    @pytest.fixture
    def user(self):
        """Fixture to create a User instance."""
        return User(client=MagicMock())

    def test_get_user_authenticated(self, user):
        """Test getting authenticated user information."""
        mock_response = {"username": "testuser", "id": 1}
        user._get = MagicMock(return_value=mock_response)

        result = user.get_user()

        user._get.assert_called_once_with(endpoint="/user")
        assert result == mock_response

    def test_get_user_with_username(self, user):
        """Test getting specific user information."""
        mock_response = {"username": "other_user", "id": 2}
        user._get = MagicMock(return_value=mock_response)

        result = user.get_user(username="other_user")

        user._get.assert_called_once_with(endpoint="/users/other_user")
        assert result == mock_response

    def test_get_workflow_jobs(self, user):
        """Test getting workflow jobs with status filter."""
        mock_response = {"jobs": []}
        user._get = MagicMock(return_value=mock_response)
        user._build_get_workflow_jobs_params = MagicMock(return_value={"status": "success"})

        result = user.get_workflow_jobs(status="success", page=1, limit=10)

        user._build_get_workflow_jobs_params.assert_called_once_with(status="success", page=1, limit=10)
        user._get.assert_called_once_with(endpoint="/user/actions/jobs", params={"status": "success"})
        assert result == mock_response

    def test_get_user_level_runners_all(self, user):
        """Test getting all user-level runners."""
        mock_response = {"runners": []}
        user._get = MagicMock(return_value=mock_response)

        result = user.get_user_level_runners()

        user._get.assert_called_once_with(endpoint="/user/actions/runners")
        assert result == mock_response

    def test_get_user_level_runners_specific(self, user):
        """Test getting a specific user-level runner."""
        mock_response = {"runner": {"id": "123"}}
        user._get = MagicMock(return_value=mock_response)

        result = user.get_user_level_runners(runner_id="123")

        user._get.assert_called_once_with(endpoint="/user/actions/runners/123")
        assert result == mock_response

    def test_get_registration_token(self, user):
        """Test getting registration token."""
        mock_response = {"token": "abc123"}
        user._get = MagicMock(return_value=mock_response)

        result = user.get_registration_token()

        user._get.assert_called_once_with(endpoint="/user/actions/runners/registration-token")
        assert result == mock_response

    def test_delete_user_level_runner(self, user):
        """Test deleting a user-level runner."""
        mock_response = {}
        user._delete = MagicMock(return_value=mock_response)

        result = user.delete_user_level_runner(runner_id="123")

        user._delete.assert_called_once_with(endpoint="/user/actions/runners/123")
        assert result == mock_response

    def test_get_workflow_runs(self, user):
        """Test getting workflow runs with filters."""
        mock_response = {"runs": []}
        user._get = MagicMock(return_value=mock_response)
        user._build_get_workflow_runs_params = MagicMock(return_value={"event": "push"})

        result = user.get_workflow_runs(event="push", status="success")

        user._build_get_workflow_runs_params.assert_called_once_with(
            event="push", branch=None, status="success", actor=None, head_sha=None, page=None, limit=None
        )
        user._get.assert_called_once_with(endpoint="/user/actions/runs", params={"event": "push"})
        assert result == mock_response
