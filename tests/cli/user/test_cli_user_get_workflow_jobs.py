"""Unit tests for get_workflow_jobs CLI command."""

from unittest.mock import MagicMock, patch

import pytest
import typer

from gitea.cli.user.get_workflow_jobs import get_workflow_jobs_command


class TestGetWorkflowJobsCommand:
    """Test cases for get_workflow_jobs_command."""

    @pytest.fixture
    def mock_ctx(self):
        """Fixture to create a mock Typer context."""
        ctx = MagicMock(spec=typer.Context)
        ctx.obj = {
            "token": "test_token",
            "base_url": "https://test.gitea.com",
            "timeout": 60,
        }
        return ctx

    @patch("gitea.cli.utils.execute_api_command")
    def test_get_workflow_jobs_command_with_status(self, mock_execute_api_command, mock_ctx):
        """Test getting workflow jobs with status filter."""
        mock_execute_api_command.return_value = None

        get_workflow_jobs_command(ctx=mock_ctx, status="success")

        # Verify execute_api_command was called
        mock_execute_api_command.assert_called_once()

        # Extract the api_call closure and verify it calls the correct method
        call_kwargs = mock_execute_api_command.call_args[1]
        api_call = call_kwargs["api_call"]

        # Mock the Gitea client and verify the closure calls get_workflow_jobs with correct params
        with patch("gitea.client.gitea.Gitea") as mock_gitea_class:
            mock_client = MagicMock()
            mock_gitea_class.return_value.__enter__.return_value = mock_client
            mock_client.user.get_workflow_jobs.return_value = {"jobs": []}

            result = api_call()

            # Verify the api_call invoked the correct method with correct parameters
            mock_client.user.get_workflow_jobs.assert_called_once_with(
                status="success", page=None, limit=None, timeout=60
            )
            assert result == {"jobs": []}

    @patch("gitea.cli.utils.execute_api_command")
    def test_get_workflow_jobs_command_with_pagination(self, mock_execute_api_command, mock_ctx):
        """Test getting workflow jobs with pagination."""
        mock_execute_api_command.return_value = None

        get_workflow_jobs_command(ctx=mock_ctx, status="pending", page=1, limit=10)

        # Verify execute_api_command was called
        mock_execute_api_command.assert_called_once()

        # Extract the api_call closure and verify it calls with pagination params
        call_kwargs = mock_execute_api_command.call_args[1]
        api_call = call_kwargs["api_call"]

        with patch("gitea.client.gitea.Gitea") as mock_gitea_class:
            mock_client = MagicMock()
            mock_gitea_class.return_value.__enter__.return_value = mock_client
            mock_client.user.get_workflow_jobs.return_value = {"jobs": []}

            result = api_call()

            # Verify pagination parameters are passed correctly
            mock_client.user.get_workflow_jobs.assert_called_once_with(status="pending", page=1, limit=10, timeout=60)
            assert result == {"jobs": []}

    @patch("gitea.cli.utils.execute_api_command")
    def test_get_workflow_jobs_command_no_token(self, mock_execute_api_command, mock_ctx):
        """Test command with no token."""
        mock_ctx.obj["token"] = None
        mock_execute_api_command.return_value = None

        get_workflow_jobs_command(ctx=mock_ctx, status="failure")

        # Verify execute_api_command was called
        mock_execute_api_command.assert_called_once()

        # Extract the api_call closure and verify it still calls with None token
        call_kwargs = mock_execute_api_command.call_args[1]
        api_call = call_kwargs["api_call"]

        with patch("gitea.client.gitea.Gitea") as mock_gitea_class:
            mock_client = MagicMock()
            mock_gitea_class.return_value.__enter__.return_value = mock_client
            mock_client.user.get_workflow_jobs.return_value = {"jobs": []}

            _result = api_call()

            # Verify Gitea was initialized with None token
            mock_gitea_class.assert_called_once_with(token=None, base_url="https://test.gitea.com")
            mock_client.user.get_workflow_jobs.assert_called_once()
