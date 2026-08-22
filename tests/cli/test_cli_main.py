"""Unit tests for CLI main module."""

import importlib
import inspect
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
from gitea.watch.state import STATE_FILE_ENV
from tests.cli.envelope import parse_envelope
from tests.cli.rendering import unrendered
from tests.cli.tree import leaf_command_paths, leaf_commands
from tests.transport import RecordingSession

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

# Options the CLI's naming convention declares optional at the parser level so
# that omitting one asks for the owner-wide target, and which a command whose
# endpoint has no owner-wide form therefore rejects at run time instead. A walk
# that synthesized only Click-required options would invoke those commands
# without a repository and see the rejection rather than an envelope, so these
# are supplied whenever the leaf declares them. Passing them is harmless where
# they really are optional: it names a repository target instead of an
# owner-wide one.
_SCOPE_OPTIONS = frozenset({"--owner", "--repository", "--issue-id", "--dependency-issue-id"})

# The helpers a command routes its result and its failures through. A command
# with a human-readable rendering of its own calls `execute_api_call` and reports
# the result itself, where one that only reports an API result calls
# `execute_api_command` and lets it print the envelope; both share the error
# handling the walks below assert on.
_API_HELPERS = ("execute_api_command", "execute_api_call")


def _noop_invocation(command: Any) -> list[str]:
    """Build a harmless argument list satisfying a leaf command's required options.

    Values are synthesized from each parameter's type rather than listed per
    command, so a newly added required option cannot silently drop its command
    out of the walk. The scope and identifier options of `_SCOPE_OPTIONS` are
    supplied as well, since a command can require one of those at run time
    while declaring it optional. Confirmation flags are passed so no invocation
    blocks on stdin.

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

        if not param.required and flag not in _SCOPE_OPTIONS:
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


def _logged_message(call: Any) -> str:
    """Render the message of a logging call as the user reads it.

    Asserting on a message through the handler that renders it makes the
    assertion depend on the terminal: `RichHandler` lays a record out as a table
    and appends the emitting frame - the module and line the record came from -
    at the right of the first line, so a message long enough to wrap at the
    running terminal's width gets that frame laid between its halves. Reading
    the record the CLI logged instead keeps the wording under test and leaves
    the layout out of it.

    Args:
        call: Recorded call to a `logging` method, as `mock.call_args` gives it.

    Returns:
        The logged message with its arguments interpolated.

    """
    template, *args = call.args
    return str(template) % tuple(args)


class _StubGitea:
    """Stand-in for the API client whose every endpoint returns an empty listing.

    Attribute access resolves to the same object, so one stub serves every
    command without the walk having to know which resource and endpoint each one
    reaches for. The payload is an empty list because commands that page through
    a listing stop on the first short page, and a non-empty page of a fixed size
    would page forever. `get_issue` is the exception: it is declared as a real
    method so that it answers with a single issue, because the `project issue`
    commands resolve `--issue-id` to a global ID by reading the `id` off it and
    an empty listing would fail that resolution for a reason that has nothing to
    do with the command under test.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Accept whatever credentials the command passes and ignore them.

        Args:
            *args: Ignored.
            **kwargs: Ignored.

        """
        self._removed_card_ids: set[int] = set()

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

    def get_issue(self, *args: Any, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        """Return the single issue that an issue lookup is expected to return.

        Args:
            *args: Ignored.
            **kwargs: Ignored.

        Returns:
            One issue and its metadata.

        """
        return {"id": 1}, {"status_code": 200}

    def list_project_columns(self, *args: Any, **kwargs: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Return the single column of the board the walk's project has.

        Declared for the same reason as `get_issue`: `project issue move` finds
        the issue's card before moving it, and a board with no columns holds no
        card, so an empty listing would fail that command for a reason that has
        nothing to do with the command under test.

        Args:
            *args: Ignored.
            **kwargs: Ignored.

        Returns:
            One column and its metadata.

        """
        return [{"id": 1}], {"status_code": 200}

    def list_project_column_issues(self, *args: Any, **kwargs: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Return the single card the board's column holds, until a removal takes it off.

        Its ID is the one `get_issue` answers with, so the card is the issue the
        `project issue` commands resolved.

        Args:
            *args: Ignored.
            **kwargs: Ignored.

        Returns:
            One issue and its metadata, or an empty listing once that issue's
            card has been removed.

        """
        cards = [] if 1 in self._removed_card_ids else [{"id": 1}]
        return cards, {"status_code": 200}

    def remove_issue_from_project_column(
        self, *args: Any, **kwargs: Any
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Take a card off the board, as the removal endpoint does.

        Declared for the mirror image of the reason `list_project_columns` is:
        `project issue remove` walks the board again after removing a card and
        reports a card still on it, so a stub answering the removal and then
        going on listing the card would fail that command for a reason that has
        nothing to do with the command under test.

        Args:
            *args: Ignored.
            **kwargs: The call's arguments, of which the issue is read.

        Returns:
            The empty payload and the metadata the endpoint answers with.

        """
        issue_id = kwargs.get("issue_id")
        if isinstance(issue_id, int):
            self._removed_card_ids.add(issue_id)
        return [], {"status_code": 204}

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

    def remove_issue_from_project_column(
        self, *args: Any, **kwargs: Any
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Fail as the removal endpoint does when the connection cannot be established.

        Declared because the stub this extends answers removals with a method of
        its own, which the failing `__call__` below would otherwise never be
        reached for: an endpoint answering on an instance that cannot be reached
        is not the instance this stands in for.

        Args:
            *args: Passed on to the failing call.
            **kwargs: Passed on to the failing call.

        Returns:
            Nothing: the call this delegates to raises.

        """
        return self(*args, **kwargs)

    def __call__(self, *args: Any, **kwargs: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Fail as an endpoint does when the connection cannot be established.

        Args:
            *args: Ignored.
            **kwargs: Ignored.

        Raises:
            ConnectionError: Always, in the form the HTTP layer raises it.

        """
        raise requests.ConnectionError("Failed to establish a new connection: [Errno 111] Connection refused")

    def get_issue(self, *args: Any, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        """Fail as every other endpoint of an unreachable instance does.

        The base stub answers issue lookups with a payload, which would let a
        command past the lookup and leave the walk testing the endpoint after it
        rather than the one it reached first.

        Args:
            *args: Ignored.
            **kwargs: Ignored.

        Returns:
            Never; the call always raises.

        """
        return self(*args, **kwargs)

    def list_project_columns(self, *args: Any, **kwargs: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Fail as every other endpoint of an unreachable instance does.

        Overridden for the same reason as `get_issue`: the base stub describes a
        board, which would carry a command that walks one past the listing and
        leave the walk testing whichever endpoint it reached next.

        Args:
            *args: Ignored.
            **kwargs: Ignored.

        Returns:
            Never; the call always raises.

        """
        return self(*args, **kwargs)

    def list_project_column_issues(self, *args: Any, **kwargs: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Fail as every other endpoint of an unreachable instance does.

        Args:
            *args: Ignored.
            **kwargs: Ignored.

        Returns:
            Never; the call always raises.

        """
        return self(*args, **kwargs)


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
        assert "--output" in unrendered(result.stdout)

    def test_output_option_accepted_by_every_subcommand(self) -> None:
        """Every leaf subcommand should be reachable through `--output json`."""
        paths = leaf_command_paths(get_command(app))

        # Guard against the walk silently finding nothing to check.
        assert len(paths) > 1
        assert ["config", "list"] in paths

        for path in paths:
            result = runner.invoke(app, ["--output", "json", *path, "--help"])
            assert result.exit_code == 0, f"{path}: {result.output}"

    def test_json_mode_routes_every_subcommand_through_a_structured_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Every leaf subcommand should emit the envelope, and nothing else, in JSON mode.

        Strategy: walk the command tree and actually run each leaf, rather than
        only asking it for `--help`. Arguments are synthesized from the leaf's
        required options, the API client is replaced by a stub, and the config
        and the watch cache point at throwaway files, so no invocation touches
        the network or anything of the user's. Checking only that `--output
        json` is *accepted* would pass a command that registers the option and
        then prints prose; checking stdout only passes a command that really
        routed through `emit` or `execute_api_command`.
        """
        monkeypatch.setenv(STATE_FILE_ENV, str(tmp_path / "watch-state.json"))
        leaves = [
            (path, command) for path, command in leaf_commands(get_command(app)) if path not in _NO_NOOP_INVOCATION
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
        for path, command in leaf_commands(get_command(app)):
            module = importlib.import_module(command.callback.__module__)
            source = inspect.getsource(module)

            assert any(helper in source for helper in _API_HELPERS) or "emit(" in source, f"{path}: {module.__name__}"

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

    def test_every_api_subcommand_names_the_base_url_when_unreachable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Every command reaching the API should name the host it tried.

        `execute_api_command` is handed a callable, not the client, so it can
        only name the host if the command passes it: a call site that omits the
        base URL leaves the user with a message that never says which instance
        was tried. Checking the helper alone would not catch that, so the walk
        runs each leaf command for real against a client that refuses to
        connect. Commands that never reach the API - the `config` ones - are
        skipped by looking for the helper in their module source.
        """
        monkeypatch.setenv(STATE_FILE_ENV, str(tmp_path / "watch-state.json"))

        leaves = [
            (path, command)
            for path, command in leaf_commands(get_command(app))
            if path not in _NO_NOOP_INVOCATION
            and any(
                helper in inspect.getsource(importlib.import_module(command.callback.__module__))
                for helper in _API_HELPERS
            )
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


class TestOptionNaming:
    """The naming convention every resource command follows.

    One shape addresses a target in every family: `--owner` names the owner,
    `--repository` narrows it to one repository of that owner and is optional
    everywhere, and an entity is named by `--<entity>-id`. The assertions here
    are over the whole command tree rather than over one family, because a
    convention that holds in most places is what the CLI already had.
    """

    def test_no_command_requires_the_repository_at_the_parser_level(self) -> None:
        """`--repository` should be optional wherever it is offered.

        Omitting it asks for the owner's own target, so a command that declared
        it required would answer that invocation with a usage error rather than
        with the message naming what it needs - and would put back the
        difference between the families that the convention removes.
        """
        offered = [
            (path, param)
            for path, command in leaf_commands(get_command(app))
            for param in command.params
            if "--repository" in param.opts
        ]

        # Guard against the walk finding nothing to assert about.
        assert len(offered) > 10
        assert [path for path, param in offered if param.required] == []

    def test_every_command_that_narrows_by_repository_also_names_an_owner(self) -> None:
        """`--repository` should never be the only half of the scope offered."""
        for path, command in leaf_commands(get_command(app)):
            flags = {opt for param in command.params for opt in param.opts}
            if "--repository" in flags:
                assert "--owner" in flags, path

    def test_an_issue_is_named_by_issue_id_everywhere(self) -> None:
        """No command should name an issue by a third spelling.

        `--index` and `--dependency-index` are the deprecated names of
        `--issue-id` and `--dependency-issue-id`. Any other option ending in
        `index` would be a new spelling of the same concept, which is what this
        convention exists to prevent.
        """
        deprecated = {"--index", "--dependency-index"}

        for path, command in leaf_commands(get_command(app)):
            flags = {opt for param in command.params for opt in param.opts}
            assert {flag for flag in flags if flag.endswith("index")} <= deprecated, path

    def test_a_deprecated_issue_option_never_appears_without_its_replacement(self) -> None:
        """A command accepting `--index` should accept `--issue-id` too."""
        replacements = {"--index": "--issue-id", "--dependency-index": "--dependency-issue-id"}
        seen: set[str] = set()

        for path, command in leaf_commands(get_command(app)):
            flags = {opt for param in command.params for opt in param.opts}
            for deprecated, replacement in replacements.items():
                if deprecated in flags:
                    seen.add(deprecated)
                    assert replacement in flags, path

        # Guard against the walk passing because it found no deprecated option.
        assert seen == set(replacements)

    def test_the_deprecated_issue_options_are_hidden_from_help(self) -> None:
        """`--help` should offer one name per concept, not the retired one too."""
        for path, command in leaf_commands(get_command(app)):
            for param in command.params:
                if {"--index", "--dependency-index"} & set(param.opts):
                    assert param.hidden, path

    def test_a_command_that_needs_a_repository_says_which_option_to_pass(self, tmp_path: Path) -> None:
        """Omitting `--repository` where the endpoint needs one should be actionable.

        The point of declaring the option optional is that the message can
        mention the organization case, so the message is what is asserted here -
        not merely that the command failed. It is read off the record the CLI
        logged rather than off the rendered output, so that the assertion holds
        at every terminal width.
        """
        config_path = tmp_path / "config.yaml"
        _write_stub_config(config_path, with_stub_account=True)

        with (
            patch("gitea.client.gitea.Gitea", _StubGitea),
            patch("gitea.cli.utils.api.logger") as mock_logger,
        ):
            result = runner.invoke(
                app,
                ["--config-path", str(config_path), "issue", "get", "--owner", _STUB, "--issue-id", "1"],
            )

        assert result.exit_code == 1
        # A failed command leaves stdout parsable, as every other error does.
        assert result.stdout == ""
        assert mock_logger.error.call_count == 1
        message = _logged_message(mock_logger.error.call_args)
        assert "'gitea-cli issue get' needs a repository: pass --repository REPOSITORY." in message
        # The user is told why the option looked optional in the first place.
        assert "'gitea-cli project'" in message

    def test_a_command_that_needs_an_issue_says_which_option_to_pass(self, tmp_path: Path) -> None:
        """Naming no issue should point at `--issue-id` rather than at `--index`."""
        config_path = tmp_path / "config.yaml"
        _write_stub_config(config_path, with_stub_account=True)

        with (
            patch("gitea.client.gitea.Gitea", _StubGitea),
            patch("gitea.cli.utils.api.logger") as mock_logger,
        ):
            result = runner.invoke(
                app,
                ["--config-path", str(config_path), "issue", "get", "--owner", _STUB, "--repository", _STUB],
            )

        assert result.exit_code == 1
        assert result.stdout == ""
        assert mock_logger.error.call_count == 1
        assert "'gitea-cli issue get' needs an issue: pass --issue-id NUMBER." in _logged_message(
            mock_logger.error.call_args
        )

    def test_the_deprecated_index_still_names_an_issue(self, tmp_path: Path) -> None:
        """`--index` should keep working, so scripts written against it survive.

        The invocation runs through the real logging handler, so the deprecation
        warning it triggers is asserted to have been rendered to stderr and to
        have stayed out of the envelope on stdout. What the warning says is
        asserted in `test_the_deprecated_index_names_its_replacement`, which
        reads the record rather than the layout.
        """
        config_path = tmp_path / "config.yaml"
        _write_stub_config(config_path, with_stub_account=True)

        with patch("gitea.client.gitea.Gitea", _StubGitea):
            result = runner.invoke(
                app,
                [
                    "--config-path",
                    str(config_path),
                    "--output",
                    "json",
                    "issue",
                    "get",
                    "--owner",
                    _STUB,
                    "--repository",
                    _STUB,
                    "--index",
                    "15",
                ],
            )

        assert result.exit_code == 0
        # In JSON mode stdout belongs to the envelope alone, so a warning that
        # leaked onto it fails this parse rather than reaching a consumer.
        assert parse_envelope(result.stdout)["data"] == {"id": 1}
        assert "deprecated" in unrendered(result.stderr)

    def test_the_deprecated_index_names_its_replacement(self, tmp_path: Path) -> None:
        """Using `--index` should say what to use instead of it."""
        config_path = tmp_path / "config.yaml"
        _write_stub_config(config_path, with_stub_account=True)

        with (
            patch("gitea.client.gitea.Gitea", _StubGitea),
            patch("gitea.cli.utils.options.logger") as mock_logger,
        ):
            result = runner.invoke(
                app,
                [
                    "--config-path",
                    str(config_path),
                    "issue",
                    "get",
                    "--owner",
                    _STUB,
                    "--repository",
                    _STUB,
                    "--index",
                    "15",
                ],
            )

        assert result.exit_code == 0
        assert mock_logger.warning.call_count == 1
        warning = _logged_message(mock_logger.warning.call_args)
        assert "--index is deprecated" in warning
        assert "pass --issue-id instead" in warning

    def test_the_new_issue_option_warns_about_nothing(self, tmp_path: Path) -> None:
        """`--issue-id` should not carry the deprecation warning of the name it replaces."""
        config_path = tmp_path / "config.yaml"
        _write_stub_config(config_path, with_stub_account=True)

        with patch("gitea.client.gitea.Gitea", _StubGitea):
            result = runner.invoke(
                app,
                [
                    "--config-path",
                    str(config_path),
                    "issue",
                    "get",
                    "--owner",
                    _STUB,
                    "--repository",
                    _STUB,
                    "--issue-id",
                    "15",
                ],
            )

        assert result.exit_code == 0
        assert "deprecated" not in unrendered(result.stderr)

    def test_omitting_the_repository_asks_for_the_owners_own_target(self, tmp_path: Path) -> None:
        """A command with an owner-wide endpoint should use it when `--repository` is omitted.

        `project get` is the family the convention is taken from: omitting the
        repository has to keep reaching the organization's project rather than
        become the error the repository-scoped families report. Succeeding is not
        enough to show that, because a command reaching the repository endpoint
        with an empty repository in the path would succeed against a stub too, so
        the URL each invocation asked for is what is asserted - once with the
        repository named and once without, since the pair is what makes the
        difference the option's optionality is for.
        """
        config_path = tmp_path / "config.yaml"
        _write_stub_config(config_path, with_stub_account=True)
        arguments = ["--config-path", str(config_path), "project", "get", "--owner", _STUB, "--project-id", "1"]

        organization_session = RecordingSession(payload={"id": 1})
        with patch("gitea.client.gitea.requests.Session", return_value=organization_session):
            organization = runner.invoke(app, arguments)

        repository_session = RecordingSession(payload={"id": 1})
        with patch("gitea.client.gitea.requests.Session", return_value=repository_session):
            repository = runner.invoke(app, [*arguments, "--repository", _STUB])

        assert organization.exit_code == 0, organization.output
        assert repository.exit_code == 0, repository.output
        assert organization_session.requests == [("GET", f"https://gitea.invalid/api/v1/orgs/{_STUB}/projects/1")]
        assert repository_session.requests == [
            ("GET", f"https://gitea.invalid/api/v1/repos/{_STUB}/{_STUB}/projects/1")
        ]


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
            "org": "Commands for managing organizations.",
            "repo": "Commands for managing repositories.",
            "watch": "Commands for watching issues for changes.",
        }
        calls = mock_add_typer.call_args_list
        assert len(calls) == len(expected)
        for name, help_text in expected.items():
            assert any(call.kwargs.get("name") == name and call.kwargs.get("help") == help_text for call in calls)
