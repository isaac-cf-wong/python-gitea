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

        mock_execute_api_command.assert_called_once_with(
            ctx=mock_ctx, api_call=mock_execute_api_command.call_args[1]["api_call"], command_name="get-workflow-jobs"
        )

    @patch("gitea.cli.utils.execute_api_command")
    def test_get_workflow_jobs_command_with_pagination(self, mock_execute_api_command, mock_ctx):
        """Test getting workflow jobs with pagination."""
        mock_execute_api_command.return_value = None

        get_workflow_jobs_command(ctx=mock_ctx, status="pending", page=1, limit=10)

        mock_execute_api_command.assert_called_once()

    @patch("gitea.cli.utils.execute_api_command")
    def test_get_workflow_jobs_command_no_token(self, mock_execute_api_command, mock_ctx):
        """Test command with no token."""
        mock_ctx.obj["token"] = None
        mock_execute_api_command.return_value = None

        get_workflow_jobs_command(ctx=mock_ctx, status="failure")

        mock_execute_api_command.assert_called_once()
