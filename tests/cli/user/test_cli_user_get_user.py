"""Unit tests for get_user CLI command."""

from unittest.mock import MagicMock, patch

import pytest
import typer

from gitea.cli.user.get_user import get_user_command


class TestGetUserCommand:
    """Test cases for get_user_command."""

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
    def test_get_user_command_authenticated(self, mock_execute_api_command, mock_ctx):
        """Test getting authenticated user information."""
        mock_execute_api_command.return_value = None

        get_user_command(ctx=mock_ctx)

        # Verify execute_api_command was called
        mock_execute_api_command.assert_called_once()

        # Extract the api_call closure and verify it calls the correct method
        call_kwargs = mock_execute_api_command.call_args[1]
        api_call = call_kwargs["api_call"]

        # Mock the Gitea client and verify the closure calls get_user with correct params
        with patch("gitea.client.gitea.Gitea") as mock_gitea_class:
            mock_client = MagicMock()
            mock_gitea_class.return_value.__enter__.return_value = mock_client
            mock_client.user.get_user.return_value = {"username": "testuser", "id": 1}

            result = api_call()

            # Verify the api_call invoked the correct method with correct parameters
            mock_client.user.get_user.assert_called_once_with(username=None, timeout=60)
            assert result == {"username": "testuser", "id": 1}

    @patch("gitea.cli.utils.execute_api_command")
    def test_get_user_command_with_username(self, mock_execute_api_command, mock_ctx):
        """Test getting specific user information."""
        mock_execute_api_command.return_value = None

        get_user_command(ctx=mock_ctx, username="testuser")

        # Verify execute_api_command was called
        mock_execute_api_command.assert_called_once()

        # Extract the api_call closure and verify it calls with username
        call_kwargs = mock_execute_api_command.call_args[1]
        api_call = call_kwargs["api_call"]

        with patch("gitea.client.gitea.Gitea") as mock_gitea_class:
            mock_client = MagicMock()
            mock_gitea_class.return_value.__enter__.return_value = mock_client
            mock_client.user.get_user.return_value = {"username": "testuser", "id": 2}

            result = api_call()

            # Verify username parameter is passed correctly
            mock_client.user.get_user.assert_called_once_with(username="testuser", timeout=60)
            assert result == {"username": "testuser", "id": 2}

    @patch("gitea.cli.utils.execute_api_command")
    def test_get_user_command_no_token(self, mock_execute_api_command, mock_ctx):
        """Test command with no token."""
        mock_ctx.obj["token"] = None
        mock_execute_api_command.return_value = None

        get_user_command(ctx=mock_ctx)

        # Verify execute_api_command was called
        mock_execute_api_command.assert_called_once()

        # Extract the api_call closure and verify it still calls with None token
        call_kwargs = mock_execute_api_command.call_args[1]
        api_call = call_kwargs["api_call"]

        with patch("gitea.client.gitea.Gitea") as mock_gitea_class:
            mock_client = MagicMock()
            mock_gitea_class.return_value.__enter__.return_value = mock_client
            mock_client.user.get_user.return_value = {"username": "testuser", "id": 1}

            _result = api_call()

            # Verify Gitea was initialized with None token
            mock_gitea_class.assert_called_once_with(token=None, base_url="https://test.gitea.com")
            mock_client.user.get_user.assert_called_once()
