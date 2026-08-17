"""Unit tests for CLI main module."""

import importlib
import inspect
import re
from pathlib import Path
from typing import Any, Self
from unittest.mock import MagicMock, patch

import pytest
import requests
import typer
import yaml
from typer.main import get_command
from typer.testing import CliRunner

from gitea.cli.main import LoggingLevel, app, main, register_commands, setup_logging, version_callback
from gitea.cli.output import OutputFormat, get_output_format
from gitea.version import __version__
from tests.cli.envelope import parse_envelope

runner = CliRunner()

# Value synthesized for the string options a leaf command requires, and the name
# of the account the throwaway config carries so that `config` commands acting on
# an existing account find one.
_STUB = "stub"

# Leaf commands for which no harmless no-op invocation exists - one that could
# not get past argument validation without a live server, say. Empty today; add
# a path here together with the reason rather than weakening the assertions in
# `test_json_mode_routes_every_subcommand_through_a_structured_path`.
_NO_NOOP_INVOCATION: frozenset[tuple[str, ...]] = frozenset()

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def _unrendered(text: str) -> str:
    r"""Strip rich's styling and line breaks from help text.

    Rich decides how to render the help from its environment, and two of its
    decisions can break an option name apart:

    * When it believes it is writing to a terminal - which Typer forces on
      whenever `GITHUB_ACTIONS`, `FORCE_COLOR` or `PY_COLORS` is set - it emits
      colour escapes, and it styles the leading dash of an option separately, so
      `--output` reaches stdout as `\x1b[1;36m-\x1b[0m\x1b[1;36m-output\x1b[0m`.
    * At a narrow terminal width it wraps the option column mid-word.

    Neither is part of what these tests assert, so remove the escapes and all
    whitespace. Dropping whitespace cannot manufacture an option name that the
    help does not document, so the assertions still discriminate.
    """
    return "".join(_ANSI_ESCAPE.sub("", text).split())


def _leaf_commands(command: Any, prefix: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], Any]]:
    """Collect every leaf command in a Click command tree with its argument path.

    Groups are recognized by carrying a `commands` mapping, so the walk does not
    depend on the Click classes Typer happens to build the tree from.

    Args:
        command: Command to walk.
        prefix: Names of the groups traversed so far.

    Returns:
        One `(argument path, command)` pair per leaf command.

    """
    subcommands = getattr(command, "commands", None)
    if subcommands:
        return [pair for name, sub in subcommands.items() for pair in _leaf_commands(sub, (*prefix, name))]
    return [(prefix, command)]


def _leaf_command_paths(command: Any, prefix: tuple[str, ...] = ()) -> list[list[str]]:
    """Collect the argument path of every leaf command in a Click command tree.

    Args:
        command: Command to walk.
        prefix: Names of the groups traversed so far.

    Returns:
        One list of argument names per leaf command.

    """
    return [list(path) for path, _ in _leaf_commands(command, prefix)]


def _noop_invocation(command: Any) -> list[str]:
    """Build a harmless argument list satisfying a leaf command's required options.

    Values are synthesized from each parameter's type rather than listed per
    command, so a newly added required option cannot silently drop its command
    out of the walk. Confirmation flags are passed so no invocation blocks on
    stdin.

    Args:
        command: Leaf command to build arguments for.

    Returns:
        The command-line arguments to append after the command path.

    """
    args: list[str] = []
    for param in command.params:
        flag = next((opt for opt in param.opts if opt.startswith("--")), None)

        if getattr(param, "is_flag", False):
            if flag == "--force":
                args.append(flag)
            continue

        if not param.required:
            continue

        choices = getattr(param.type, "choices", None)
        if choices:
            value = str(choices[0])
        elif getattr(param.type, "name", "") in {"int", "integer", "float"}:
            value = "1"
        else:
            value = _STUB

        args.extend([flag, value] if flag else [value])

    return args


def _write_stub_config(path: Path, *, with_stub_account: bool) -> None:
    """Write a throwaway configuration file for a no-op invocation.

    Args:
        path: Location to write the configuration to.
        with_stub_account: Whether to include an account named `_STUB`, which the
            `config` commands operating on an existing account need and `config
            add` needs absent.

    """
    accounts = {"seed": {"name": "seed", "base_url": "https://gitea.invalid", "token": "seed-token"}}
    if with_stub_account:
        accounts[_STUB] = {"name": _STUB, "base_url": "https://gitea.invalid", "token": "stub-token"}

    path.write_text(yaml.safe_dump({"default_account": "seed", "accounts": accounts}))


class _StubGitea:
    """Stand-in for the API client whose every endpoint returns an empty listing.

    Attribute access resolves to the same object, so one stub serves every
    command without the walk having to know which resource and endpoint each one
    reaches for. The payload is an empty list because commands that page through
    a listing stop on the first short page, and a non-empty page of a fixed size
    would page forever.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Accept whatever credentials the command passes and ignore them.

        Args:
            *args: Ignored.
            **kwargs: Ignored.

        """

    def __getattr__(self, name: str) -> Self:
        """Resolve any resource or endpoint name to this same stub.

        Args:
            name: Attribute requested by the command.

        Returns:
            This stub.

        """
        return self

    def __call__(self, *args: Any, **kwargs: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Return the `(data, metadata)` pair every endpoint is expected to return.

        Args:
            *args: Ignored.
            **kwargs: Ignored.

        Returns:
            An empty listing and its metadata.

        """
        return [], {"status_code": 200}

    def __enter__(self) -> Self:
        """Enter the client context manager.

        Returns:
            This stub.

        """
        return self

    def __exit__(self, *exc_info: object) -> bool:
        """Leave the client context manager without suppressing exceptions.

        Args:
            *exc_info: Ignored exception information.

        Returns:
            False, so exceptions propagate.

        """
        return False


class _UnreachableGitea(_StubGitea):
    """Stand-in for the API client of an instance that cannot be reached.

    The base URL is kept as a real attribute rather than left to `__getattr__`,
    because the helpers that build the unreachable message read it off the
    client, and a stub standing in for it would hide the host under test.
    """

    def __init__(self, *args: Any, base_url: str | None = None, **kwargs: Any) -> None:
        """Record the base URL the command passed and ignore the credentials.

        Args:
            *args: Ignored.
            base_url: The base URL the command resolved, kept for the message.
            **kwargs: Ignored.

        """
        super().__init__(*args, **kwargs)
        self.base_url = base_url

    def __call__(self, *args: Any, **kwargs: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Fail as an endpoint does when the connection cannot be established.

        Args:
            *args: Ignored.
            **kwargs: Ignored.

        Raises:
            ConnectionError: Always, in the form the HTTP layer raises it.

        """
        raise requests.ConnectionError("Failed to establish a new connection: [Errno 111] Connection refused")


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

    def test_output_option_is_documented_on_the_root_app(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """`--output` should be listed among the global options."""
        # Rich drops the whole options table at very narrow widths, so pin one
        # wide enough that the assertion cannot depend on the caller's terminal.
        monkeypatch.setenv("COLUMNS", "200")
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "--output" in _unrendered(result.stdout)

    def test_output_option_accepted_by_every_subcommand(self) -> None:
        """Every leaf subcommand should be reachable through `--output json`."""
        paths = _leaf_command_paths(get_command(app))

        # Guard against the walk silently finding nothing to check.
        assert len(paths) > 1
        assert ["config", "list"] in paths

        for path in paths:
            result = runner.invoke(app, ["--output", "json", *path, "--help"])
            assert result.exit_code == 0, f"{path}: {result.output}"

    def test_json_mode_routes_every_subcommand_through_a_structured_path(self, tmp_path: Path) -> None:
        """Every leaf subcommand should emit the envelope, and nothing else, in JSON mode.

        Strategy: walk the command tree and actually run each leaf, rather than
        only asking it for `--help`. Arguments are synthesized from the leaf's
        required options, the API client is replaced by a stub, and the config
        points at a throwaway file, so no invocation touches the network or the
        user's configuration. Checking only that `--output json` is *accepted*
        would pass a command that registers the option and then prints prose;
        checking stdout only passes a command that really routed through `emit`
        or `execute_api_command`.
        """
        leaves = [
            (path, command) for path, command in _leaf_commands(get_command(app)) if path not in _NO_NOOP_INVOCATION
        ]

        # Guard against the walk silently finding nothing to run.
        assert len(leaves) > 1
        assert ("config", "list") in [path for path, _ in leaves]

        config_path = tmp_path / "config.yaml"
        emitted = 0

        with patch("gitea.client.gitea.Gitea", _StubGitea):
            for path, command in leaves:
                # Re-seed per command so an earlier `config` command's write
                # cannot decide whether a later one succeeds.
                _write_stub_config(config_path, with_stub_account=path != ("config", "add"))

                result = runner.invoke(
                    app,
                    ["--config-path", str(config_path), "--output", "json", *path, *_noop_invocation(command)],
                )

                if result.exit_code == 0:
                    parse_envelope(result.stdout)
                    emitted += 1
                else:
                    # A failed command emits no envelope, but it must not leak a
                    # human-readable message onto stdout either.
                    assert result.stdout == "", f"{path}: {result.stdout!r}"

        assert emitted == len(leaves), f"only {emitted} of {len(leaves)} leaf commands emitted an envelope"

    def test_every_subcommand_module_wires_the_structured_output_path(self) -> None:
        """Every leaf subcommand's module should reference a structured-output helper.

        A static companion to the walk above: it makes the wiring visible even
        for a command whose no-op invocation is listed in `_NO_NOOP_INVOCATION`
        and therefore never run. The helpers are imported inside the command
        bodies to keep startup cheap, so the module source is what is searched.
        """
        for path, command in _leaf_commands(get_command(app)):
            module = importlib.import_module(command.callback.__module__)
            source = inspect.getsource(module)

            assert "execute_api_command" in source or "emit(" in source, f"{path}: {module.__name__}"

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

    def test_explicit_option_overrides_the_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An explicit `--output` should win over `PYTHON_GITEA_OUTPUT`."""
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

        assert runner.invoke(probe_app, ["--output", "text", "probe"]).stdout.strip() == "text"
        assert runner.invoke(probe_app, ["-o", "text", "probe"]).stdout.strip() == "text"

    def test_explicit_option_overrides_the_environment_end_to_end(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A real command should render text when the flag contradicts the environment."""
        monkeypatch.setenv("PYTHON_GITEA_OUTPUT", "json")
        config_path = tmp_path / "config.yaml"
        _write_stub_config(config_path, with_stub_account=False)

        with_flag = runner.invoke(app, ["--config-path", str(config_path), "--output", "text", "config", "list"])
        without_flag = runner.invoke(app, ["--config-path", str(config_path), "config", "list"])

        assert with_flag.exit_code == 0
        assert "Configured accounts:" in with_flag.stdout

        # The same invocation without the flag takes the format from the
        # environment, so the flag is what made the difference.
        assert without_flag.exit_code == 0
        assert parse_envelope(without_flag.stdout)["metadata"]["account_count"] == 1

    def test_invalid_environment_value_is_rejected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """An unparsable `PYTHON_GITEA_OUTPUT` should fail loudly, not silently default."""
        monkeypatch.setenv("PYTHON_GITEA_OUTPUT", "garbage")
        # Keep the error on one line so the assertions do not depend on wrapping.
        monkeypatch.setenv("COLUMNS", "200")
        config_path = tmp_path / "config.yaml"
        _write_stub_config(config_path, with_stub_account=False)

        # Point at a throwaway config so that a regression letting the invalid
        # value through cannot read the developer's own configuration instead.
        result = runner.invoke(app, ["--config-path", str(config_path), "config", "list"])

        assert result.exit_code == 2
        assert result.stdout == ""

        message = " ".join(result.stderr.split())
        assert "PYTHON_GITEA_OUTPUT" in message
        assert "'garbage' is not one of 'text', 'json'" in message

    def test_callback_defaults_to_text(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Omitting the option should leave the CLI in text mode."""
        monkeypatch.delenv("PYTHON_GITEA_CONFIG_PATH", raising=False)
        ctx = MagicMock()

        main(ctx, config_path=None, verbose=LoggingLevel.INFO, output=OutputFormat.TEXT, version=False)

        assert ctx.obj == {"config_path": None, "output": OutputFormat.TEXT}


class TestUnreachableInstance:
    """Tests for how the CLI reports an instance it could not reach."""

    def test_every_api_subcommand_names_the_base_url_when_unreachable(self, tmp_path: Path) -> None:
        """Every command reaching the API should name the host it tried.

        `execute_api_command` is handed a callable, not the client, so it can
        only name the host if the command passes it: a call site that omits the
        base URL leaves the user with a message that never says which instance
        was tried. Checking the helper alone would not catch that, so the walk
        runs each leaf command for real against a client that refuses to
        connect. Commands that never reach the API - the `config` ones - are
        skipped by looking for the helper in their module source.
        """
        leaves = [
            (path, command)
            for path, command in _leaf_commands(get_command(app))
            if path not in _NO_NOOP_INVOCATION
            and "execute_api_command" in inspect.getsource(importlib.import_module(command.callback.__module__))
        ]

        # Guard against the filter silently leaving nothing to run.
        assert len(leaves) > 1
        assert ("issue", "get") in [path for path, _ in leaves]

        config_path = tmp_path / "config.yaml"
        _write_stub_config(config_path, with_stub_account=True)

        for path, command in leaves:
            with (
                patch("gitea.client.gitea.Gitea", _UnreachableGitea),
                patch("gitea.cli.utils.api.logger") as mock_logger,
            ):
                result = runner.invoke(
                    app,
                    ["--config-path", str(config_path), *path, *_noop_invocation(command)],
                )

            assert result.exit_code == 1, f"{path}: {result.output}"
            # A traceback says no more than the message here, so none is logged.
            assert mock_logger.exception.call_count == 0, f"{path}: logged a traceback"
            assert mock_logger.error.call_count == 1, f"{path}: {mock_logger.error.call_args_list}"
            message = str(mock_logger.error.call_args[0][1])
            assert "Could not reach the Gitea API at https://gitea.invalid" in message, f"{path}: {message}"


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
