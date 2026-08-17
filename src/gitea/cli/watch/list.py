"""Report the issues that changed since the last watch run.

The command is built to be run from cron. On a tick where nothing changed it
prints nothing at all, so a watchdog wrapping it has nothing to forward, nothing
to page and nothing to charge for; on a tick where something did, it prints one
line per change, and `--output json` gives the same changes as the envelope
every other command emits.

What it compares against is the cache described in `gitea.watch.state`, which it
updates as part of the run - before the report is written, so that a failure to
write it is reported as an error with nothing on stdout, as every other failure
in this CLI is. `--dry-run` leaves the cache exactly as it was, which makes the
same changes come back on the next run.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Annotated, Any

import typer

from gitea.utils.pagination import PAGE_SIZE, collect_all_pages
from gitea.watch.changes import detect_changes, format_change, issue_key, issue_snapshot
from gitea.watch.state import STATE_FILE_ENV, load_state, record_scope, resolve_state_path, save_state, scope_snapshots

logger = logging.getLogger("gitea")

COMMAND_NAME = "gitea-cli watch list"


@dataclass(frozen=True)
class _Scope:
    """One thing being watched, and the key its snapshots are cached under.

    Attributes:
        key: Key the scope's snapshots are recorded under in the cache.
        repository: Repository the scope is narrowed to, or None for the owner.
        project_id: Project the scope watches the board of, or None to watch the
            open issues of the repository instead.

    """

    key: str
    repository: str | None
    project_id: int | None


def build_scopes(owner: str, repositories: list[str], project_ids: list[int]) -> list[_Scope]:
    """Work out what a run watches from the options naming it.

    Every repository named is a scope of its own, and so is every project, which
    is how one invocation reports what changed across several repositories and
    boards at once. A project is resolved the way every other `project` command
    resolves one: against the repository when one is named, and against the owner
    itself when none is.

    Args:
        owner: The user or organization owning what is watched.
        repositories: The repositories named, in the order they were named.
        project_ids: The projects named, in the order they were named.

    Returns:
        One scope per repository and per project, repositories first.

    Raises:
        CommandError: If nothing was named to watch, or if projects were named
            alongside more than one repository, which leaves no single scope for
            them to be resolved against.

    """
    from gitea.cli.utils.errors import CommandError  # noqa: PLC0415

    if not repositories and not project_ids:
        raise CommandError(
            f"'{COMMAND_NAME}' needs something to watch: pass --repository REPOSITORY for a repository's open "
            f"issues, --project-id ID for a project's board, or both. Either may be repeated to watch several."
        )

    if project_ids and len(repositories) > 1:
        raise CommandError(
            f"'{COMMAND_NAME}' cannot resolve --project-id against {len(repositories)} repositories: a project "
            f"belongs either to one repository or to the owner itself. Pass --project-id with at most one "
            f"--repository, or watch the repositories in a separate invocation."
        )

    scope_repository = repositories[0] if len(repositories) == 1 else None

    scopes = [_Scope(key=f"repo:{owner}/{name}", repository=name, project_id=None) for name in repositories]
    scopes += [
        _Scope(
            key=f"project:{owner}/{scope_repository}/{identifier}"
            if scope_repository
            else f"project:{owner}/{identifier}",
            repository=scope_repository,
            project_id=identifier,
        )
        for identifier in project_ids
    ]
    return scopes


def _holder(issue: dict[str, Any], owner: str, repository: str | None) -> tuple[str, str] | None:
    """Work out which repository an issue's comments have to be listed under.

    A board holds cards from any repository of its owner, so the repository the
    scope was named with is not the one every issue on it lives in. The issue
    payload names its own, and the scope's repository is the fallback for a
    payload that does not.

    Args:
        issue: The issue data returned by the API.
        owner: The owner the scope was named with.
        repository: The repository the scope was narrowed to, or None.

    Returns:
        The owner and name of the repository holding the issue, or None when
        neither the payload nor the scope says.

    """
    payload = issue.get("repository")
    if isinstance(payload, dict):
        name, holder = payload.get("name"), payload.get("owner")
        if isinstance(name, str) and isinstance(holder, str):
            return holder, name

    return (owner, repository) if repository is not None else None


def _comments(client: Any, holder: tuple[str, str], number: Any) -> list[dict[str, Any]]:
    """Fetch every comment on one issue.

    Args:
        client: The API client.
        holder: The owner and name of the repository holding the issue.
        number: The number of the issue, as its payload carries it.

    Returns:
        The issue's comments, or an empty list when the payload names no issue
        to list them for.

    """
    if not isinstance(number, int) or isinstance(number, bool):
        return []

    comments, _ = collect_all_pages(
        lambda page: client.comment.list_comments(
            owner=holder[0],
            repository=holder[1],
            index=number,
            page=page,
            limit=PAGE_SIZE,
        )
    )
    return comments


def _scope_issues(client: Any, owner: str, scope: _Scope) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch the issues a scope currently holds, across every page of them.

    Args:
        client: The API client.
        owner: The owner the scope was named with.
        scope: The scope to fetch.

    Returns:
        A tuple of the issues and the metadata of the last response.

    """
    if scope.project_id is None:
        return collect_all_pages(
            lambda page: client.issue.list_issues(
                owner=owner,
                repository=scope.repository,
                state="open",
                page=page,
                limit=PAGE_SIZE,
            )
        )

    columns, metadata = collect_all_pages(
        lambda page: client.project.list_project_columns(
            owner=owner,
            repository=scope.repository,
            project_id=scope.project_id,
            page=page,
            limit=PAGE_SIZE,
        )
    )

    issues: list[dict[str, Any]] = []
    for column in columns:
        identifier = column.get("id") if isinstance(column, dict) else None
        if not isinstance(identifier, int) or isinstance(identifier, bool):
            continue
        column_issues, metadata = collect_all_pages(
            lambda page, column_id=identifier: client.project.list_project_column_issues(
                owner=owner,
                repository=scope.repository,
                project_id=scope.project_id,
                column_id=column_id,
                page=page,
                limit=PAGE_SIZE,
            )
        )
        issues.extend(column_issues)

    return issues, metadata


def _snapshots(client: Any, owner: str, scope: _Scope, issues: list[Any]) -> dict[str, dict[str, Any]]:
    """Reduce the issues of a scope to the snapshots the cache holds.

    Args:
        client: The API client.
        owner: The owner the scope was named with.
        scope: The scope the issues came from.
        issues: The issues the scope currently holds.

    Returns:
        The snapshot of each issue, keyed by its global ID. An entry that is not
        an issue, or that carries no global ID to key it by, is skipped: it
        cannot be compared against anything, and dropping it is better than
        reporting a change on every run because it never matches.

    """
    snapshots: dict[str, dict[str, Any]] = {}

    for issue in issues:
        if not isinstance(issue, dict):
            continue
        key = issue_key(issue)
        if key is None:
            logger.warning(
                "Skipping an issue of %s that carries no global ID, which is what it would be cached by.", scope.key
            )
            continue

        holder = _holder(issue, owner, scope.repository)
        if holder is None:
            logger.warning(
                "Not reading the comments of issue %s of %s: its payload does not name the repository holding it, "
                "so comment changes on it are not reported.",
                key,
                scope.key,
            )

        snapshots[key] = issue_snapshot(
            issue,
            _comments(client, holder, issue.get("number")) if holder else [],
            repository=f"{holder[0]}/{holder[1]}" if holder else None,
        )

    return snapshots


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
            "--dry-run", help="Report the changes without recording them, so the next run reports them again."
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
        scopes = build_scopes(owner, list(repository or []), list(project_id or []))
        state = load_state(state_path)

        changes: list[dict[str, Any]] = []
        baselined: list[str] = []
        issue_count = 0
        metadata: dict[str, Any] = {}

        with Gitea(token=token, base_url=base_url) as client:
            for scope in scopes:
                issues, metadata = _scope_issues(client, owner, scope)
                snapshots = _snapshots(client, owner, scope, issues)
                previous = scope_snapshots(state, scope.key)

                if previous is None:
                    baselined.append(scope.key)
                changes.extend({**change, "scope": scope.key} for change in detect_changes(snapshots, previous))

                record_scope(state, scope.key, snapshots)
                issue_count += len(snapshots)

        if not dry_run:
            try:
                save_state(state_path, state)
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
