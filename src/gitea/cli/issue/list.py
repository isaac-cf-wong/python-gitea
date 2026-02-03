"""List issues command."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

import typer


def list_command(  # noqa: PLR0913
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    repository: Annotated[str, typer.Option("--repository", help="Name of the repository.")],
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
            help="Base URL of the GitHub platform. If not provided, the base URL from the specified account will be used.",
        ),
    ] = None,
) -> None:
    """List issues in a repository.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository.
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
        page: The page number for pagination.
        limit: The number of issues per page.
        account_name: Name of the account to use for authentication.
        token: Token for authentication. If not provided, the token from the specified account will be used.
        base_url: Base URL of the Gitea platform. If not provided, the base URL from the specified account will be used.

    """
    from typing import Any  # noqa: PLC0415

    from gitea.cli.utils.api import execute_api_command  # noqa: PLC0415
    from gitea.cli.utils.auth import get_auth_params  # noqa: PLC0415
    from gitea.cli.utils.convert import list_str_to_list_int_or_none  # noqa: PLC0415
    from gitea.client.gitea import Gitea  # noqa: PLC0415

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
        with Gitea(token=token, base_url=base_url) as client:
            return client.issue.list_issues(
                owner=owner,
                repository=repository,
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
                page=page,
                limit=limit,
            )

    execute_api_command(api_call=api_call, command_name="gitea-cli issue list")
