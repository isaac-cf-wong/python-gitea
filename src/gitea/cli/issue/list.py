"""List issues command.

`--issue-ids` narrows the listing to a known set of issues. Gitea's listing takes
no such filter, so the set is applied here, over the listing the other filters
select: its pages are walked until every requested issue has been seen or the
listing ends, and the issues are emitted in the order they were asked for. An
issue of the set that the other filters exclude - a closed one under the default
`--state open`, say - is simply not listed, which is what makes "which of these
are open" one call; `metadata.not_listed` names each such issue, so it can be
told apart from one that was listed. `issue get` is the command that fails on an
issue that does not exist.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Any, Literal

import typer

from gitea.cli.utils.options import REPOSITORY_REQUIRED_HELP

ISSUE_IDS_FILTER_HELP = (
    "List only these issues, given as numbers separated by commas, in the order given. "
    "The other filters still apply. Cannot be combined with --page."
)


def list_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    repository: Annotated[str | None, typer.Option("--repository", help=REPOSITORY_REQUIRED_HELP)] = None,
    state: Annotated[
        Literal["closed", "open", "all"] | None, typer.Option("--state", help="Filter issues by state.")
    ] = None,
    labels: Annotated[
        list[str] | None,
        typer.Option("--labels", help="Filter issues by labels."),
    ] = None,
    search_string: Annotated[
        str | None,
        typer.Option("--search-string", help="Filter issues by search string."),
    ] = None,
    issue_type: Annotated[
        Literal["issues", "pulls"] | None,
        typer.Option("--issue-type", help="Filter by issue type."),
    ] = None,
    milestones: Annotated[
        list[str] | None,
        typer.Option("--milestones", help="Filter issues by milestones."),
    ] = None,
    since: Annotated[
        datetime | None,
        typer.Option("--since", help="Filter issues updated since this time."),
    ] = None,
    before: Annotated[
        datetime | None,
        typer.Option("--before", help="Filter issues updated before this time."),
    ] = None,
    created_by: Annotated[
        str | None,
        typer.Option("--created-by", help="Filter issues created by this user."),
    ] = None,
    assigned_by: Annotated[
        str | None,
        typer.Option("--assigned-by", help="Filter issues assigned to this user."),
    ] = None,
    mentioned_by: Annotated[
        str | None,
        typer.Option("--mentioned-by", help="Filter issues mentioning this user."),
    ] = None,
    issue_ids: Annotated[
        str | None,
        typer.Option("--issue-ids", help=ISSUE_IDS_FILTER_HELP),
    ] = None,
    page: Annotated[
        int | None,
        typer.Option("--page", help="The page number for pagination."),
    ] = None,
    limit: Annotated[
        int | None,
        typer.Option("--limit", help="The number of issues per page."),
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
    """List issues in a repository.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository, which this command requires.
        state: Filter issues by state.
        labels: Filter issues by labels.
        search_string: Filter issues by search string.
        issue_type: Filter by issue type.
        milestones: Filter issues by milestones.
        since: Filter issues updated since this time.
        before: Filter issues updated before this time.
        created_by: Filter issues created by this user.
        assigned_by: Filter issues assigned to this user.
        mentioned_by: Filter issues mentioning this user.
        issue_ids: List only these issues, given as comma-separated numbers.
        page: The page number for pagination.
        limit: The number of issues per page.
        account_name: Name of the account to use for authentication.
        token: Token for authentication. If not provided, the token from the specified account will be used.
        base_url: Base URL of the Gitea platform. If not provided, the base URL from the specified account will be used.

    """
    from gitea.cli.utils.api import execute_api_command  # noqa: PLC0415
    from gitea.cli.utils.auth import get_auth_params  # noqa: PLC0415
    from gitea.cli.utils.convert import list_str_to_list_int_or_none  # noqa: PLC0415
    from gitea.cli.utils.options import require_repository  # noqa: PLC0415
    from gitea.client.gitea import Gitea  # noqa: PLC0415
    from gitea.utils.pagination import PAGE_SIZE  # noqa: PLC0415

    command = "gitea-cli issue list"
    token, base_url = get_auth_params(
        config_path=ctx.obj.get("config_path"),
        account_name=account_name,
        token=token,
        base_url=base_url,
    )

    milestones_values = list_str_to_list_int_or_none(milestones)

    def api_call() -> tuple[dict[str, Any] | list[dict[str, Any]], dict[str, Any]]:
        """List issues in a repository.

        Returns:
            The issue information as a dictionary.

        """
        target_repository = require_repository(repository, command=command)
        requested = _requested_issues(issue_ids, page, command=command)

        with Gitea(token=token, base_url=base_url) as client:

            def fetch(page_number: int | None, page_size: int | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
                return client.issue.list_issues(
                    owner=owner,
                    repository=target_repository,
                    state=state,
                    labels=labels,
                    search_string=search_string,
                    issue_type=issue_type,
                    milestones=milestones_values,
                    since=since,
                    before=before,
                    created_by=created_by,
                    assigned_by=assigned_by,
                    mentioned_by=mentioned_by,
                    page=page_number,
                    limit=page_size,
                )

            if requested is None:
                return fetch(page, limit)
            return _list_requested(requested, lambda number: fetch(number, limit or PAGE_SIZE))

    execute_api_command(api_call=api_call, base_url=base_url, command_name=command)


def _requested_issues(issue_ids: str | None, page: int | None, *, command: str) -> list[int] | None:
    """Read the set of issues the listing is narrowed to.

    Args:
        issue_ids: The value passed as --issue-ids, or None when it was omitted.
        page: The value passed as --page, or None when it was omitted.
        command: The command being run, named as the user invoked it.

    Returns:
        The issue numbers in the order given, each once, or None when the
        listing is not narrowed.

    Raises:
        CommandError: If the set is empty or holds a value that is not an issue
            number, or --page was passed with it: the set is looked for across
            every page, so a page number would have nothing to select.

    """
    from gitea.cli.issue.ids import parse_issue_numbers  # noqa: PLC0415
    from gitea.cli.utils.errors import CommandError  # noqa: PLC0415

    if issue_ids is None:
        return None
    if page is not None:
        raise CommandError(
            f"'{command}': --issue-ids is looked for across every page of the listing, so --page cannot be "
            f"combined with it. Drop --page; --limit still sets how many issues each request asks for."
        )
    numbers = parse_issue_numbers(issue_ids, source="--issue-ids", command=command)
    if not numbers:
        raise CommandError(f"'{command}': --issue-ids names no issue. Pass the numbers separated by commas.")
    return list(dict.fromkeys(numbers))


def _list_requested(
    numbers: list[int],
    fetch_page: Callable[[int], tuple[list[dict[str, Any]], dict[str, Any]]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Walk a listing until every requested issue has been seen, and keep only those.

    Args:
        numbers: The requested issue numbers, each once.
        fetch_page: Callable returning the items and metadata of the given page number.

    Returns:
        A tuple containing the requested issues the listing holds, in the order
        requested, and the metadata of the last response with `not_listed`
        naming the requested issues it does not hold.

    """
    from gitea.utils.pagination import iter_pages  # noqa: PLC0415

    wanted = set(numbers)
    found: dict[int, dict[str, Any]] = {}
    metadata: dict[str, Any] = {}
    for batch, page_metadata in iter_pages(fetch_page):
        metadata = page_metadata
        found.update({issue["number"]: issue for issue in batch if issue.get("number") in wanted})
        if len(found) == len(wanted):
            break

    issues = [found[number] for number in numbers if number in found]
    return issues, {**metadata, "not_listed": [number for number in numbers if number not in found]}
