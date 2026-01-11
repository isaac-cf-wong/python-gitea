"""Unit tests for AsyncUser resource."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from gitea.user.async_user import AsyncUser


class TestAsyncUser:
    """Test cases for AsyncUser resource."""

    @pytest.fixture
    def async_user(self):
        """Fixture to create an AsyncUser instance."""
        return AsyncUser(client=MagicMock())

    @pytest.mark.asyncio
    async def test_get_user_authenticated(self, async_user):
        """Test getting authenticated user information."""
        mock_response = {"username": "testuser", "id": 1}
        async_user._get = AsyncMock(return_value=mock_response)

        result = await async_user.get_user()

        async_user._get.assert_called_once_with(endpoint="/user")
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_get_user_with_username(self, async_user):
        """Test getting specific user information."""
        mock_response = {"username": "other_user", "id": 2}
        async_user._get = AsyncMock(return_value=mock_response)

        result = await async_user.get_user(username="other_user")

        async_user._get.assert_called_once_with(endpoint="/users/other_user")
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_get_workflow_jobs(self, async_user):
        """Test getting workflow jobs with status filter."""
        mock_response = {"jobs": []}
        async_user._get = AsyncMock(return_value=mock_response)
        async_user._build_get_workflow_jobs_params = MagicMock(return_value={"status": "success"})

        result = await async_user.get_workflow_jobs(status="success", page=1, limit=10)

        async_user._build_get_workflow_jobs_params.assert_called_once_with(status="success", page=1, limit=10)
        async_user._get.assert_called_once_with(endpoint="/user/actions/jobs", params={"status": "success"})
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_get_user_level_runners_all(self, async_user):
        """Test getting all user-level runners."""
        mock_response = {"runners": []}
        async_user._get = AsyncMock(return_value=mock_response)

        result = await async_user.get_user_level_runners()

        async_user._get.assert_called_once_with(endpoint="/user/actions/runners")
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_get_user_level_runners_specific(self, async_user):
        """Test getting a specific user-level runner."""
        mock_response = {"runner": {"id": "123"}}
        async_user._get = AsyncMock(return_value=mock_response)

        result = await async_user.get_user_level_runners(runner_id="123")

        async_user._get.assert_called_once_with(endpoint="/user/actions/runners/123")
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_get_registration_token(self, async_user):
        """Test getting registration token."""
        mock_response = {"token": "abc123"}
        async_user._get = AsyncMock(return_value=mock_response)

        result = await async_user.get_registration_token()

        async_user._get.assert_called_once_with(endpoint="/user/actions/runners/registration-token")
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_delete_user_level_runner(self, async_user):
        """Test deleting a user-level runner."""
        mock_response = {}
        async_user._delete = AsyncMock(return_value=mock_response)

        result = await async_user.delete_user_level_runner(runner_id="123")

        async_user._delete.assert_called_once_with(endpoint="/user/actions/runners/123")
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_get_workflow_runs(self, async_user):
        """Test getting workflow runs with filters."""
        mock_response = {"runs": []}
        async_user._get = AsyncMock(return_value=mock_response)
        async_user._build_get_workflow_runs_params = MagicMock(return_value={"event": "push"})

        result = await async_user.get_workflow_runs(event="push", status="success")

        async_user._build_get_workflow_runs_params.assert_called_once_with(
            event="push", branch=None, status="success", actor=None, head_sha=None, page=None, limit=None
        )
        async_user._get.assert_called_once_with(endpoint="/user/actions/runs", params={"event": "push"})
        assert result == mock_response
