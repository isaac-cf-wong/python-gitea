"""Unit tests for CLI main module."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from gitea.cli.main import LoggingLevel, app, register_commands, setup_logging

runner = CliRunner()


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

        mock_get_logger.assert_called_once_with("gitea")
        mock_logger.setLevel.assert_called_with("DEBUG")
        mock_logger.removeHandler.assert_called_once()  # Now called since handlers exist
        mock_rich_handler_class.assert_called_once()
        mock_logger.addHandler.assert_called_once_with(mock_handler)
        assert mock_logger.propagate is False


class TestMainCallback:
    """Tests for the main CLI callback."""

    def test_main_help(self) -> None:
        """Test that main help works."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "gitea" in result.stdout

    def test_main_verbose_info(self) -> None:
        """Test verbose level option INFO."""
        result = runner.invoke(app, ["--verbose", "INFO", "config", "--help"])
        assert result.exit_code == 0

    def test_main_verbose_debug(self) -> None:
        """Test verbose level option DEBUG."""
        result = runner.invoke(app, ["--verbose", "DEBUG", "config", "--help"])
        assert result.exit_code == 0

    def test_main_config_path(self, tmp_path) -> None:
        """Test passing config path."""
        config_file = tmp_path / "config.yaml"
        result = runner.invoke(app, ["--config-path", str(config_file), "config", "--help"])
        assert result.exit_code == 0


class TestRegisterCommands:
    """Test cases for register_commands function."""

    @patch("gitea.cli.main.app.add_typer")
    def test_register_commands(self, mock_add_typer):
        """Test that register_commands adds all sub-applications."""
        register_commands()

        expected = {
            "config": "Commands for managing configurations.",
            "issue": "Commands for managing issues.",
            "pull-request": "Commands for managing pull requests.",
            "user": "Commands for managing users.",
            "comment": "Commands for managing comments.",
            "label": "Commands for managing labels.",
            "milestone": "Commands for managing milestones.",
        }
        calls = mock_add_typer.call_args_list
        assert len(calls) == len(expected)
        for name, help_text in expected.items():
            assert any(call.kwargs.get("name") == name and call.kwargs.get("help") == help_text for call in calls)
