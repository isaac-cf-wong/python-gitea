"""Unit tests for CLI main module."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.main import get_command
from typer.testing import CliRunner

from gitea.cli.main import LoggingLevel, app, main, register_commands, setup_logging, version_callback
from gitea.cli.output import OutputFormat, get_output_format
from gitea.version import __version__

runner = CliRunner()


def _leaf_command_paths(command: Any, prefix: tuple[str, ...] = ()) -> list[list[str]]:
    """Collect the argument path of every leaf command in a Click command tree.

    Groups are recognized by carrying a `commands` mapping, so the walk does not
    depend on the Click classes Typer happens to build the tree from.

    Args:
        command: Command to walk.
        prefix: Names of the groups traversed so far.

    Returns:
        One list of argument names per leaf command.

    """
    subcommands = getattr(command, "commands", None)
    if subcommands:
        return [path for name, sub in subcommands.items() for path in _leaf_command_paths(sub, (*prefix, name))]
    return [list(prefix)]


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


class TestOutputOption:
    """Tests for the global `--output` option."""

    def test_output_option_is_documented_on_the_root_app(self) -> None:
        """`--output` should be listed among the global options."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "--output" in result.stdout

    def test_output_option_accepted_by_every_subcommand(self) -> None:
        """Every leaf subcommand should be reachable through `--output json`."""
        paths = _leaf_command_paths(get_command(app))

        # Guard against the walk silently finding nothing to check.
        assert len(paths) > 1
        assert ["config", "list"] in paths

        for path in paths:
            result = runner.invoke(app, ["--output", "json", *path, "--help"])
            assert result.exit_code == 0, f"{path}: {result.output}"

    def test_output_short_option_accepted(self) -> None:
        """`-o` should be an alias for `--output`."""
        result = runner.invoke(app, ["-o", "json", "config", "list", "--help"])

        assert result.exit_code == 0

    def test_output_option_rejects_unknown_format(self) -> None:
        """An unsupported format should be a usage error naming the valid ones."""
        result = runner.invoke(app, ["--output", "yaml", "config", "list", "--help"])

        assert result.exit_code == 2
        assert "text" in result.output
        assert "json" in result.output

    def test_callback_stores_requested_format_on_the_context(self) -> None:
        """The root callback should put the requested format on `ctx.obj`."""
        probe_app = typer.Typer()
        probe_app.callback()(main)

        @probe_app.command("probe")
        def probe(ctx: typer.Context) -> None:
            """Print the output format seen by a subcommand.

            Args:
                ctx: Typer context.

            """
            typer.echo(get_output_format(ctx).value)

        assert runner.invoke(probe_app, ["--output", "json", "probe"]).stdout.strip() == "json"
        assert runner.invoke(probe_app, ["probe"]).stdout.strip() == "text"

    def test_callback_reads_format_from_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """`PYTHON_GITEA_OUTPUT` should set the format when the flag is absent."""
        probe_app = typer.Typer()
        probe_app.callback()(main)

        @probe_app.command("probe")
        def probe(ctx: typer.Context) -> None:
            """Print the output format seen by a subcommand.

            Args:
                ctx: Typer context.

            """
            typer.echo(get_output_format(ctx).value)

        monkeypatch.setenv("PYTHON_GITEA_OUTPUT", "json")

        assert runner.invoke(probe_app, ["probe"]).stdout.strip() == "json"

    def test_callback_defaults_to_text(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Omitting the option should leave the CLI in text mode."""
        monkeypatch.delenv("PYTHON_GITEA_CONFIG_PATH", raising=False)
        ctx = MagicMock()

        main(ctx, config_path=None, verbose=LoggingLevel.INFO, output=OutputFormat.TEXT, version=False)

        assert ctx.obj == {"config_path": None, "output": OutputFormat.TEXT}


class TestVersionOption:
    """Tests for the --version flag."""

    def test_version_flag_prints_version_and_exits(self) -> None:
        """`--version` should print the package version and exit successfully."""
        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert result.stdout.strip() == __version__

    def test_version_callback_exits_when_set(self) -> None:
        """version_callback should raise Exit when the flag is provided."""
        with pytest.raises(typer.Exit):
            version_callback(True)

    def test_version_callback_is_noop_when_unset(self, capsys) -> None:
        """version_callback should print nothing when the flag is absent."""
        assert version_callback(False) is None
        assert capsys.readouterr().out == ""


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
            "notification": "Commands for managing notifications.",
            "project": "Commands for managing projects.",
        }
        calls = mock_add_typer.call_args_list
        assert len(calls) == len(expected)
        for name, help_text in expected.items():
            assert any(call.kwargs.get("name") == name and call.kwargs.get("help") == help_text for call in calls)
