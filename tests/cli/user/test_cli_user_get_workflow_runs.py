"""Unit tests for get_workflow_runs CLI command."""

from unittest.mock import MagicMock, patch

import pytest
import typer

from gitea.cli.user.get_workflow_runs import get_workflow_runs_command


class TestGetWorkflowRunsCommand:
    """Test cases for get_workflow_runs_command."""

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
    def test_get_workflow_runs_command_no_filters(self, mock_execute_api_command, mock_ctx):
        """Test getting workflow runs without filters."""
        mock_execute_api_command.return_value = None

        get_workflow_runs_command(ctx=mock_ctx)

        mock_execute_api_command.assert_called_once_with(
            ctx=mock_ctx, api_call=mock_execute_api_command.call_args[1]["api_call"], command_name="get-workflow-runs"
        )

    @patch("gitea.cli.utils.execute_api_command")
    def test_get_workflow_runs_command_with_filters(self, mock_execute_api_command, mock_ctx):
        """Test getting workflow runs with various filters."""
        mock_execute_api_command.return_value = None

        get_workflow_runs_command(
            ctx=mock_ctx,
            event="push",
            branch="main",
            status="success",
            actor="testuser",
            head_sha="abc123",
            page=1,
            limit=10,
        )

        mock_execute_api_command.assert_called_once()

    @patch("gitea.cli.utils.execute_api_command")
    def test_get_workflow_runs_command_no_token(self, mock_execute_api_command, mock_ctx):
        """Test command with no token."""
        mock_ctx.obj["token"] = None
        mock_execute_api_command.return_value = None

        get_workflow_runs_command(ctx=mock_ctx, status="failure")

        mock_execute_api_command.assert_called_once()
