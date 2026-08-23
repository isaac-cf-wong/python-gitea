"""Report the issues that changed since the last watch run.

The command is built to be run on a schedule. On a tick where nothing changed it
prints nothing at all, so whatever wraps it - a cron entry mailing its output, a
script deciding whether to notify anyone - has nothing to forward and nothing to
act on. On a tick where something did, it prints one line per change, and
`--output json` gives the same changes as the envelope every other command
emits.

What it compares against is the cache described in `gitea.watch.state`, which it
updates as part of the run - before the report is written, so that a failure to
write it is reported as an error with nothing on stdout, as every other failure
in this CLI is.

`--dry-run`, spelled `--no-advance` for a caller who reads the cache as
something to advance rather than a run as something to rehearse, leaves the
cache exactly as it was, which makes the same changes come back on the next run.
It is what separates detecting a change from consuming it: a consumer that saw a
change but could not act on it - it was already busy, the run it would have
started was still in flight - leaves the cache where it is and meets the change
again, where a run that advanced it has quietly spent the only notification
there was going to be. Such a consumer commits the cache itself, once it has
acted, with `gitea-cli watch advance`.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

import typer

from gitea.cli.watch.scopes import build_scopes, collect_snapshots
from gitea.watch.changes import detect_changes, format_change
from gitea.watch.state import STATE_FILE_ENV, load_state, resolve_state_path, save_scopes, scope_snapshots

logger = logging.getLogger("gitea")

COMMAND_NAME = "gitea-cli watch list"


def list_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repositories and projects to watch.")],
    repository: Annotated[
        list[str] | None,
        typer.Option("--repository", help="Name of a repository to watch the open issues of. Repeat to watch several."),
    ] = None,
    project_id: Annotated[
        list[int] | None,
        typer.Option("--project-id", help="ID of a project to watch the board of. Repeat to watch several."),
    ] = None,
    state_file: Annotated[
        str | None,
        typer.Option(
            "--state-file",
            envvar=STATE_FILE_ENV,
            help="Path of the cache of issue snapshots. Defaults to the user cache directory.",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "--no-advance",
            help=(
                "Report the changes without recording them, so the next run reports them again. Commit the cache "
                "once the changes have been acted on with 'gitea-cli watch advance'."
            ),
        ),
    ] = False,
    account_name: Annotated[
        str | None,
        typer.Option(
            "--account-name",
            help="Name of the account to use for authentication.",
        ),
    ] = None,
    token: Annotated[
        str | None,
        typer.Option(
            "--token",
            help="Token for authentication. If not provided, the token from the specified account will be used.",
        ),
    ] = None,
    base_url: Annotated[
        str | None,
        typer.Option(
            "--base-url",
            help="Base URL of the Gitea platform. If not provided, the base URL from the specified account will be used.",
        ),
    ] = None,
) -> None:
    """Report the issues that changed since the last run, and record the current state.

    Args:
        ctx: The Typer context.
        owner: The owner of the repositories and projects to watch.
        repository: The repositories to watch the open issues of.
        project_id: The projects to watch the board of.
        state_file: Path of the cache of issue snapshots.
        dry_run: Whether to leave the cache untouched.
        account_name: Name of the account to use for authentication.
        token: Token for authentication.
        base_url: Base URL of the Gitea platform.

    """
    from gitea.cli.output import emit  # noqa: PLC0415
    from gitea.cli.utils.api import execute_api_call  # noqa: PLC0415
    from gitea.cli.utils.auth import get_auth_params  # noqa: PLC0415
    from gitea.cli.utils.errors import CommandError  # noqa: PLC0415
    from gitea.client.gitea import Gitea  # noqa: PLC0415

    token, base_url = get_auth_params(
        config_path=ctx.obj.get("config_path"),
        account_name=account_name,
        token=token,
        base_url=base_url,
    )

    state_path = resolve_state_path(state_file)

    def api_call() -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Fetch the current state of every scope and compare it against the cache.

        Returns:
            A tuple of the changes since the recorded snapshots and metadata.

        Raises:
            CommandError: If the cache cannot be written, since a run whose
                changes were never recorded would report them again forever.

        """
        scopes = build_scopes(owner, list(repository or []), list(project_id or []), COMMAND_NAME)
        state = load_state(state_path)

        with Gitea(token=token, base_url=base_url) as client:
            recorded, metadata = collect_snapshots(client, owner, scopes)

        changes: list[dict[str, Any]] = []
        baselined: list[str] = []
        issue_count = 0

        for scope in scopes:
            snapshots = recorded[scope.key]
            previous = scope_snapshots(state, scope.key)

            if previous is None:
                baselined.append(scope.key)
            changes.extend({**change, "scope": scope.key} for change in detect_changes(snapshots, previous))

            issue_count += len(snapshots)

        if not dry_run:
            try:
                # Only the scopes this run watched are replaced, so a run that
                # finished while this one was fetching keeps what it recorded.
                save_scopes(state_path, recorded)
            except OSError as error:
                raise CommandError(
                    f"Could not write the watch cache at {state_path}: {error}. The changes reported by this run "
                    f"were not recorded, so check that the directory exists and is writable."
                ) from error

        return changes, {
            **metadata,
            "scopes": [scope.key for scope in scopes],
            "baselined_scopes": baselined,
            "issue_count": issue_count,
            "change_count": len(changes),
            "state_file": str(state_path),
            "dry_run": dry_run,
        }

    def report(data: Any, metadata: dict[str, Any]) -> None:
        """Write the changes out in the format this invocation asked for.

        Args:
            data: The changes since the recorded snapshots.
            metadata: Information about the run.

        """

        def render_text() -> None:
            """Print one line per change, and nothing at all when there are none.

            An empty report is the point of the command rather than an edge case
            of it: a cron tick that prints nothing has nothing to deliver and
            nothing to wake, which is what makes running this every few minutes
            free.
            """
            for change in data:
                typer.echo(format_change(change))

        emit(ctx, data=data, metadata=metadata, render_text=render_text)

    execute_api_call(api_call=api_call, report=report, base_url=base_url, command_name=COMMAND_NAME)
