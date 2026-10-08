"""Get issues command.

The issue is emitted with the field names the API sends, as `gitea.utils.fields`
requires. `comments` is one worth knowing about: it is the *number* of comments
on the issue and not their bodies, which `gitea-cli issue comment list` is for.
An earlier version of this command renamed it to `comment_count` to say so, and
was the only command emitting an issue that did - the same count arrived under
two names depending on which command fetched the issue, which was the worse
surprise of the two.

Several issues can be read in one run: `--issue-id` may be repeated, and
`--issue-id-file` reads a list of numbers from a file or from stdin, so a set of
hundreds need not fit on a command line. The shape of `data` follows from how
the command was invoked, never from what the API answered: one `--issue-id` and
no file gives the issue itself, as it always has; anything else gives a list of
issues in the order they were asked for, each once. An issue that does not exist
fails the run, after every requested issue has been tried, with an error naming
each missing one, so a single typo in a long list is not reported one run at a
time.

Every project an issue is on is emitted with the column its card sits in there,
resolved from that project's board: the issue payload names the projects without
saying where on them the card sits, so the column costs a walk of the board's
columns and their issue listings, a few requests per project. `--no-columns`
turns that walk off. Every project entry is then emitted as the API sent it,
without a `column_id`, and the run reads no board at all - one request per issue,
whatever boards the issues are on. It is the form to use when the issue's own
fields are what is wanted: `state`, `labels`, `title`, and reads of a set of
issues are exactly the runs that pay the walk most.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any

import typer

from gitea.cli.issue.ids import ISSUE_ID_FILE_HELP
from gitea.cli.utils.options import DEPRECATED_INDEX_HELP, REPOSITORY_REQUIRED_HELP

_NOT_FOUND = 404

ISSUE_IDS_HELP = "Issue number shown in the web UI. Repeat the option to read several issues."
ISSUE_COLUMNS_HELP = (
    "Resolve the project column of each issue's card. Pass --no-columns to leave every project entry "
    "as the API sent it and read no board, which is what a read of the issue's own fields wants."
)


def get_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    repository: Annotated[str | None, typer.Option("--repository", help=REPOSITORY_REQUIRED_HELP)] = None,
    issue_ids: Annotated[list[int] | None, typer.Option("--issue-id", help=ISSUE_IDS_HELP)] = None,
    issue_id_file: Annotated[str | None, typer.Option("--issue-id-file", help=ISSUE_ID_FILE_HELP)] = None,
    resolve_columns: Annotated[bool, typer.Option("--columns/--no-columns", help=ISSUE_COLUMNS_HELP)] = True,
    index: Annotated[int | None, typer.Option("--index", help=DEPRECATED_INDEX_HELP, hidden=True)] = None,
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
    """Get one or more issues in a repository.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository, which this command requires.
        issue_ids: The issue numbers shown in the web UI.
        issue_id_file: A file listing more issue numbers, or `-` to read them from stdin.
        resolve_columns: Whether to resolve the column each issue's card sits in.
        index: The deprecated name of `--issue-id`, which names one issue.
        account_name: Name of the account to use for authentication.
        token: Token for authentication. If not provided, the token from the specified account will be used.
        base_url: Base URL of the Gitea platform. If not provided, the base URL from the specified account will be used.

    """
    from gitea.cli.utils.api import execute_api_command  # noqa: PLC0415
    from gitea.cli.utils.auth import get_auth_params  # noqa: PLC0415
    from gitea.cli.utils.options import require_repository  # noqa: PLC0415
    from gitea.client.gitea import Gitea  # noqa: PLC0415
    from gitea.issue.project_column import ColumnListings, resolve_project_column_ids  # noqa: PLC0415

    command = "gitea-cli issue get"
    token, base_url = get_auth_params(
        config_path=ctx.obj.get("config_path"),
        account_name=account_name,
        token=token,
        base_url=base_url,
    )

    def api_call() -> tuple[dict[str, Any] | list[dict[str, Any]], dict[str, Any]]:
        """Get the issues' information.

        The column of each project an issue is on is resolved from the project's
        board, because the issue payload names the projects without saying where
        on them the issue's card sits. The issues of one run share the listings
        of their boards' columns, so a board is listed once however many of the
        issues are on it. `--no-columns` asks for no such resolution: the issues
        are emitted as the API sent them and no board is read, which is what a
        read of the issues' own fields wants.

        Returns:
            A tuple containing the issue data, or a list of it, and metadata.

        """
        target_repository = require_repository(repository, command=command)
        targets, single = _requested_issues(issue_ids, issue_id_file, index, command=command)

        with Gitea(token=token, base_url=base_url) as client:
            columns = ColumnListings() if resolve_columns else None

            def get_one(number: int) -> tuple[dict[str, Any], dict[str, Any]]:
                data, metadata = client.issue.get_issue(owner=owner, repository=target_repository, index=number)
                if not resolve_columns:
                    return data, metadata
                data = resolve_project_column_ids(
                    client=client, owner=owner, repository=target_repository, issue=data, columns=columns
                )
                return data, metadata

            if single:
                return get_one(targets[0])
            return _get_each(targets, get_one, owner=owner, repository=target_repository, command=command)

    execute_api_command(api_call=api_call, base_url=base_url, command_name=command)


def _requested_issues(
    issue_ids: list[int] | None, issue_id_file: str | None, index: int | None, *, command: str
) -> tuple[list[int], bool]:
    """Read which issues the command reads, and whether it was asked for exactly one.

    Args:
        issue_ids: The values passed as --issue-id, or None when it was omitted.
        issue_id_file: The value passed as --issue-id-file, or None when it was omitted.
        index: The value passed as the deprecated --index, or None when it was omitted.
        command: The command being run, named as the user invoked it.

    Returns:
        The issue numbers, in the order given with those of the file last, each
        once; and True when one --issue-id (or --index) and no file named them,
        which is the invocation that reports the issue itself rather than a list.

    Raises:
        CommandError: If no issue was given, or --index was combined with
            several issues.

    """
    from gitea.cli.issue.ids import read_issue_id_file  # noqa: PLC0415
    from gitea.cli.utils.errors import CommandError  # noqa: PLC0415
    from gitea.cli.utils.options import resolve_issue_id  # noqa: PLC0415

    given = list(issue_ids or [])
    if index is not None:
        if len(given) > 1 or issue_id_file is not None:
            raise CommandError(
                f"'{command}': --index names one issue and cannot be combined with several. "
                f"It is the deprecated name of --issue-id: pass --issue-id once per issue instead."
            )
        given = [resolve_issue_id(issue_id=given[0] if given else None, index=index, command=command)]

    if issue_id_file is None:
        if not given:
            raise CommandError(
                f"'{command}' needs an issue: pass --issue-id NUMBER, once per issue, or --issue-id-file PATH."
            )
        return list(dict.fromkeys(given)), len(given) == 1

    given += read_issue_id_file(issue_id_file, command=command)
    return list(dict.fromkeys(given)), False


def _get_each(
    numbers: list[int],
    get_one: Callable[[int], tuple[dict[str, Any], dict[str, Any]]],
    *,
    owner: str,
    repository: str,
    command: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Read each issue in turn, and report every one that does not exist together.

    Args:
        numbers: The issues to read.
        get_one: Callable reading one issue and returning its data and metadata.
        owner: The owner of the repository.
        repository: The name of the repository.
        command: The command being run, named as the user invoked it.

    Returns:
        A tuple containing the issues, in the order asked for, and the metadata
        of the last response.

    Raises:
        CommandError: If any of the issues does not exist. Any other failure is
            raised as it was, on the issue that met it.

    """
    from requests import HTTPError  # noqa: PLC0415

    from gitea.cli.utils.errors import CommandError  # noqa: PLC0415

    issues: list[dict[str, Any]] = []
    missing: list[int] = []
    metadata: dict[str, Any] = {}
    for number in numbers:
        try:
            data, metadata = get_one(number)
        except HTTPError as e:
            response = getattr(e, "response", None)
            if response is None or response.status_code != _NOT_FOUND:
                raise
            missing.append(number)
            continue
        issues.append(data)

    if missing:
        raise CommandError(
            f"'{command}': no issue {', '.join(str(number) for number in missing)} in {owner}/{repository}; "
            f"the other {len(issues)} of the {len(numbers)} requested exist. Nothing was printed."
        )
    return issues, {"status_code": metadata["status_code"]}
