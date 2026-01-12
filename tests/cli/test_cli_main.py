"""Unit tests for CLI main module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import typer

from gitea.cli.main import LoggingLevel, main, register_commands, setup_logging


class TestLoggingLevel:
    """Test cases for LoggingLevel enum."""

    def test_logging_levels(self):
        """Test that LoggingLevel has expected values."""
        assert LoggingLevel.NOTSET == "NOTSET"
        assert LoggingLevel.DEBUG == "DEBUG"
        assert LoggingLevel.INFO == "INFO"
        assert LoggingLevel.WARNING == "WARNING"
        assert LoggingLevel.ERROR == "ERROR"
        assert LoggingLevel.CRITICAL == "CRITICAL"


class TestSetupLogging:
    """Test cases for setup_logging function."""

    @patch("logging.getLogger")
    @patch("rich.logging.RichHandler")
    @patch("rich.console.Console")
    def test_setup_logging(self, mock_console_class, mock_rich_handler_class, mock_get_logger):
        """Test that setup_logging configures logging correctly."""
        mock_logger = MagicMock()
        mock_logger.handlers = [MagicMock()]  # Mock existing handler
        mock_get_logger.return_value = mock_logger
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        mock_handler = MagicMock()
        mock_rich_handler_class.return_value = mock_handler

        setup_logging(LoggingLevel.DEBUG)

        mock_get_logger.assert_called_once_with("python-gitea")
        mock_logger.setLevel.assert_called_with("DEBUG")
        mock_logger.removeHandler.assert_called_once()  # Now called since handlers exist
        mock_rich_handler_class.assert_called_once()
        mock_logger.addHandler.assert_called_once_with(mock_handler)
        assert mock_logger.propagate is False


class TestMain:
    """Test cases for main callback function."""

    @patch("gitea.cli.main.setup_logging")
    def test_main_callback(self, mock_setup_logging):
        """Test that main sets up context correctly."""
        ctx = MagicMock(spec=typer.Context)

        main(
            ctx=ctx,
            output=Path("/tmp/output.json"),
            token="test_token",
            base_url="https://test.gitea.com",
            timeout=60,
            verbose=LoggingLevel.DEBUG,
        )

        mock_setup_logging.assert_called_once_with(LoggingLevel.DEBUG)
        assert ctx.obj == {
            "output": Path("/tmp/output.json"),
            "token": "test_token",
            "base_url": "https://test.gitea.com",
            "timeout": 60,
        }

    @patch("gitea.cli.main.setup_logging")
    def test_main_callback_defaults(self, mock_setup_logging):
        """Test main with default values."""
        ctx = MagicMock(spec=typer.Context)

        main(ctx=ctx)

        mock_setup_logging.assert_called_once_with(LoggingLevel.INFO)
        assert ctx.obj == {
            "output": None,
            "token": None,
            "base_url": "https://gitea.com",
            "timeout": 30,
        }


class TestRegisterCommands:
    """Test cases for register_commands function."""

    @patch("gitea.cli.main.app.add_typer")
    @patch("gitea.cli.user.main.user_app")
    def test_register_commands(self, mock_user_app, mock_add_typer):
        """Test that register_commands adds the user app."""
        register_commands()

        mock_add_typer.assert_called_once_with(mock_user_app, name="user", help="Commands for managing Gitea users.")
