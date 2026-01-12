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

        # Verify execute_api_command was called
        mock_execute_api_command.assert_called_once()

        # Extract the api_call closure and verify it calls the correct method
        call_kwargs = mock_execute_api_command.call_args[1]
        api_call = call_kwargs["api_call"]

        # Mock the Gitea client and verify the closure calls delete_user_level_runner with correct params
        with patch("gitea.client.gitea.Gitea") as mock_gitea_class:
            mock_client = MagicMock()
            mock_gitea_class.return_value.__enter__.return_value = mock_client
            mock_client.user.delete_user_level_runner.return_value = {}

            result = api_call()

            # Verify the api_call invoked the correct method with correct parameters
            mock_client.user.delete_user_level_runner.assert_called_once_with(runner_id="123", timeout=60)
            assert result == {}

    @patch("gitea.cli.utils.execute_api_command")
    def test_delete_user_level_runner_command_no_token(self, mock_execute_api_command, mock_ctx):
        """Test command with no token."""
        mock_ctx.obj["token"] = None
        mock_execute_api_command.return_value = None

        delete_user_level_runner_command(ctx=mock_ctx, runner_id="123")

        # Verify execute_api_command was called
        mock_execute_api_command.assert_called_once()

        # Extract the api_call closure and verify it still calls with None token
        call_kwargs = mock_execute_api_command.call_args[1]
        api_call = call_kwargs["api_call"]

        with patch("gitea.client.gitea.Gitea") as mock_gitea_class:
            mock_client = MagicMock()
            mock_gitea_class.return_value.__enter__.return_value = mock_client
            mock_client.user.delete_user_level_runner.return_value = {}

            _result = api_call()

            # Verify Gitea was initialized with None token
            mock_gitea_class.assert_called_once_with(token=None, base_url="https://test.gitea.com")
            mock_client.user.delete_user_level_runner.assert_called_once_with(runner_id="123", timeout=60)
