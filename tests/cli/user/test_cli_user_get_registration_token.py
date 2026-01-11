"""Unit tests for get_registration_token CLI command."""

from unittest.mock import MagicMock, patch

import pytest
import typer

from gitea.cli.user.get_registration_token import get_registration_token_command


class TestGetRegistrationTokenCommand:
    """Test cases for get_registration_token_command."""

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
    def test_get_registration_token_command(self, mock_execute_api_command, mock_ctx):
        """Test successful retrieval of registration token."""
        mock_execute_api_command.return_value = None

        get_registration_token_command(ctx=mock_ctx)

        mock_execute_api_command.assert_called_once_with(
            ctx=mock_ctx,
            api_call=mock_execute_api_command.call_args[1]["api_call"],
            command_name="get-registration-token",
        )

    @patch("gitea.cli.utils.execute_api_command")
    def test_get_registration_token_command_no_token(self, mock_execute_api_command, mock_ctx):
        """Test command with no token."""
        mock_ctx.obj["token"] = None
        mock_execute_api_command.return_value = None

        get_registration_token_command(ctx=mock_ctx)

        mock_execute_api_command.assert_called_once()
