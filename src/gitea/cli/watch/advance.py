"""Record the current state of what is watched as the baseline, on demand.

`watch list` detects a change and consumes it in the same breath: it reports the
difference against the cache and advances the cache past it, so the change is
announced exactly once whether or not anyone was in a position to act on it. A
consumer that was busy - its previous run still in flight, its queue full, the
thing it would have done already being done - drops the change on the floor, and
the next run has nothing to say about it.

`watch list --no-advance` and this command are the two halves that pull those
apart. The dry run reports without consuming, and this commits the cache once
the change has actually been handled, so a change survives until someone acts on
it rather than until someone is told about it.

What it commits is the state of the instance *now*, not the state the dry run
saw. It has to be: the dry run deliberately wrote nothing down, so there is no
"then" left to commit, and re-fetching is the only thing there is. The
consequence is worth stating plainly, because it is the window this pair does
not close: a change that lands between the dry run and the advance is recorded
without ever having been reported. The `change_count` this reports is what the
advance moved the baseline past, so a caller that compares it against the count
its dry run reported can see that window when it opens; keeping the two calls
close together is what keeps it small.

Advancing a scope the cache has never held records it and reports it as
baselined, exactly as a first `watch list` would - there is nothing before it to
have moved past.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

import typer

from gitea.cli.watch.scopes import build_scopes, collect_snapshots
from gitea.watch.changes import detect_changes
from gitea.watch.state import STATE_FILE_ENV, load_state, resolve_state_path, save_scopes, scope_snapshots

logger = logging.getLogger("gitea")

COMMAND_NAME = "gitea-cli watch advance"


def _counted(count: int, noun: str) -> str:
    """Phrase a count of something, singular where there is one of it.

    Args:
        count: How many there are.
        noun: What they are, in the singular.

    Returns:
        The count and the noun, pluralized by an `s` where the count is not one.

    """
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def format_record(record: dict[str, Any]) -> str:
    """Render what the advance did to one scope as the line it prints for it.

    Args:
        record: What was recorded for the scope.

    Returns:
        One line naming the scope, how much of it was recorded, and how far the
        baseline moved - which is the part a caller checks against what its dry
        run reported.

    """
    issues = _counted(record.get("issue_count", 0), "issue")
    if record.get("baselined"):
        return f"{record.get('scope')}: recorded {issues}, baselined for the first time"

    changes = record.get("change_count", 0)
    if not changes:
        return f"{record.get('scope')}: recorded {issues}, unchanged since the cache"
    return f"{record.get('scope')}: recorded {issues}, {_counted(changes, 'change')} baselined"


def advance_command(
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
    """Record the current state of what is watched as the baseline to compare against.

    The counterpart of 'watch list --no-advance': the dry run reports the
    changes without consuming them, and this commits the cache once they have
    been acted on. What is committed is the state of the instance now, so a
    change that lands between the two is baselined without being reported;
    'change_count' says how far the baseline moved, so it can be compared
    against what the dry run reported.

    Args:
        ctx: The Typer context.
        owner: The owner of the repositories and projects to watch.
        repository: The repositories to watch the open issues of.
        project_id: The projects to watch the board of.
        state_file: Path of the cache of issue snapshots.
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
        """Fetch the current state of every scope and record it as the baseline.

        Returns:
            A tuple of what was recorded for each scope and metadata.

        Raises:
            CommandError: If the cache cannot be written, since a caller told
                the baseline had moved when it had not would act on the next
                run's report as if it were new.

        """
        scopes = build_scopes(owner, list(repository or []), list(project_id or []), COMMAND_NAME)
        state = load_state(state_path)

        with Gitea(token=token, base_url=base_url) as client:
            recorded, metadata = collect_snapshots(client, owner, scopes)

        records: list[dict[str, Any]] = []
        baselined: list[str] = []
        issue_count = 0
        change_count = 0

        for scope in scopes:
            snapshots = recorded[scope.key]
            previous = scope_snapshots(state, scope.key)

            if previous is None:
                baselined.append(scope.key)
            changes = len(detect_changes(snapshots, previous))

            records.append(
                {
                    "scope": scope.key,
                    "issue_count": len(snapshots),
                    "change_count": changes,
                    "baselined": previous is None,
                }
            )
            issue_count += len(snapshots)
            change_count += changes

        try:
            save_scopes(state_path, recorded)
        except OSError as error:
            raise CommandError(
                f"Could not write the watch cache at {state_path}: {error}. The baseline was not moved, so the "
                f"next run reports these changes again; check that the directory exists and is writable."
            ) from error

        return records, {
            **metadata,
            "scopes": [scope.key for scope in scopes],
            "baselined_scopes": baselined,
            "issue_count": issue_count,
            "change_count": change_count,
            "state_file": str(state_path),
        }

    def report(data: Any, metadata: dict[str, Any]) -> None:
        """Write what was recorded out in the format this invocation asked for.

        Args:
            data: What was recorded for each scope.
            metadata: Information about the run.

        """

        def render_text() -> None:
            """Print one line per scope recorded.

            Unlike `watch list`, this says something on every run: it is asked
            for deliberately rather than ticked on a timer, and silence from a
            command whose whole job is to write the cache is indistinguishable
            from it not having done so.
            """
            for record in data:
                typer.echo(format_record(record))

        emit(ctx, data=data, metadata=metadata, render_text=render_text)

    execute_api_call(api_call=api_call, report=report, base_url=base_url, command_name=COMMAND_NAME)
