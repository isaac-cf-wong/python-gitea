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

        # Verify execute_api_command was called
        mock_execute_api_command.assert_called_once()

        # Extract the api_call closure and verify it calls the correct method
        call_kwargs = mock_execute_api_command.call_args[1]
        api_call = call_kwargs["api_call"]

        # Mock the Gitea client and verify the closure calls get_workflow_runs with correct params
        with patch("gitea.client.gitea.Gitea") as mock_gitea_class:
            mock_client = MagicMock()
            mock_gitea_class.return_value.__enter__.return_value = mock_client
            mock_client.user.get_workflow_runs.return_value = {"runs": []}

            result = api_call()

            # Verify the api_call invoked the correct method with all None filters
            mock_client.user.get_workflow_runs.assert_called_once_with(
                event=None, branch=None, status=None, actor=None, head_sha=None, page=None, limit=None, timeout=60
            )
            assert result == {"runs": []}

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

        # Verify execute_api_command was called
        mock_execute_api_command.assert_called_once()

        # Extract the api_call closure and verify it calls with all filters
        call_kwargs = mock_execute_api_command.call_args[1]
        api_call = call_kwargs["api_call"]

        with patch("gitea.client.gitea.Gitea") as mock_gitea_class:
            mock_client = MagicMock()
            mock_gitea_class.return_value.__enter__.return_value = mock_client
            mock_client.user.get_workflow_runs.return_value = {"runs": []}

            result = api_call()

            # Verify all filter parameters are passed correctly
            mock_client.user.get_workflow_runs.assert_called_once_with(
                event="push",
                branch="main",
                status="success",
                actor="testuser",
                head_sha="abc123",
                page=1,
                limit=10,
                timeout=60,
            )
            assert result == {"runs": []}

    @patch("gitea.cli.utils.execute_api_command")
    def test_get_workflow_runs_command_no_token(self, mock_execute_api_command, mock_ctx):
        """Test command with no token."""
        mock_ctx.obj["token"] = None
        mock_execute_api_command.return_value = None

        get_workflow_runs_command(ctx=mock_ctx, status="failure")

        # Verify execute_api_command was called
        mock_execute_api_command.assert_called_once()

        # Extract the api_call closure and verify it still calls with None token
        call_kwargs = mock_execute_api_command.call_args[1]
        api_call = call_kwargs["api_call"]

        with patch("gitea.client.gitea.Gitea") as mock_gitea_class:
            mock_client = MagicMock()
            mock_gitea_class.return_value.__enter__.return_value = mock_client
            mock_client.user.get_workflow_runs.return_value = {"runs": []}

            _result = api_call()

            # Verify Gitea was initialized with None token
            mock_gitea_class.assert_called_once_with(token=None, base_url="https://test.gitea.com")
            # Verify status filter is passed correctly with None token
            mock_client.user.get_workflow_runs.assert_called_once_with(
                event=None, branch=None, status="failure", actor=None, head_sha=None, page=None, limit=None, timeout=60
            )
