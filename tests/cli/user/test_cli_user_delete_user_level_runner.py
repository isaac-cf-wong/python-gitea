"""Unit tests for delete_user_level_runner CLI command."""

from unittest.mock import MagicMock, patch

import pytest
import typer

from gitea.cli.user.delete_user_level_runner import delete_user_level_runner_command


class TestDeleteUserLevelRunnerCommand:
    """Test cases for delete_user_level_runner_command."""

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
    def test_delete_user_level_runner_command(self, mock_execute_api_command, mock_ctx):
        """Test successful deletion of user-level runner."""
        mock_execute_api_command.return_value = None

        delete_user_level_runner_command(ctx=mock_ctx, runner_id="123")

        mock_execute_api_command.assert_called_once_with(
            ctx=mock_ctx,
            api_call=mock_execute_api_command.call_args[1]["api_call"],  # The api_call function
            command_name="delete-user-level-runner",
        )

    @patch("gitea.cli.utils.execute_api_command")
    def test_delete_user_level_runner_command_no_token(self, mock_execute_api_command, mock_ctx):
        """Test command with no token."""
        mock_ctx.obj["token"] = None
        mock_execute_api_command.return_value = None

        delete_user_level_runner_command(ctx=mock_ctx, runner_id="123")

        mock_execute_api_command.assert_called_once()
