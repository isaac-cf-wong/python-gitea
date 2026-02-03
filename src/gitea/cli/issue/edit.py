"""Edit issues command."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

import typer


def edit_command(  # noqa: PLR0913
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    repository: Annotated[str, typer.Option("--repository", help="Name of the repository.")],
    index: Annotated[int, typer.Option("--index", help="Index of the issue.")],
    assignee: Annotated[
        str | None,
        typer.Option("--assignee", help="The new assignee of the issue."),
    ] = None,
    assignees: Annotated[
        list[str] | None,
        typer.Option("--assignees", help="The new assignees of the issue."),
    ] = None,
    body: Annotated[
        str | None,
        typer.Option("--body", help="The new body of the issue."),
    ] = None,
    due_date: Annotated[
        datetime | None,
        typer.Option("--due-date", help="The new due date of the issue."),
    ] = None,
    milestone: Annotated[
        int | None,
        typer.Option("--milestone", help="The new milestone of the issue."),
    ] = None,
    ref: Annotated[
        str | None,
        typer.Option("--ref", help="The new reference of the issue."),
    ] = None,
    state: Annotated[
        Literal["closed", "open"] | None,
        typer.Option("--state", help="The new state of the issue."),
    ] = None,
    title: Annotated[
        str | None,
        typer.Option("--title", help="The new title of the issue."),
    ] = None,
    unset_due_date: Annotated[
        bool | None,
        typer.Option("--unset-due-date", help="Whether to unset the due date of the issue."),
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
    """Edit a specific issue in a repository.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository.
        index: The index of the issue.
        assignee: The new assignee of the issue.
        assignees: The new assignees of the issue.
        body: The new body of the issue.
        due_date: The new due date of the issue.
        milestone: The new milestone of the issue.
        ref: The new reference of the issue.
        state: The new state of the issue.
        title: The new title of the issue.
        unset_due_date: Whether to unset the due date of the issue.
        account_name: Name of the account to use for authentication.
        token: Token for authentication. If not provided, the token from the specified account will be used.
        base_url: Base URL of the Gitea platform. If not provided, the base URL from the specified account will be used.

    """
    from typing import Any  # noqa: PLC0415

    from gitea.cli.utils.api import execute_api_command  # noqa: PLC0415
    from gitea.cli.utils.auth import get_auth_params  # noqa: PLC0415
    from gitea.client.gitea import Gitea  # noqa: PLC0415

    token, base_url = get_auth_params(
        config_path=ctx.obj.get("config_path"),
        account_name=account_name,
        token=token,
        base_url=base_url,
    )

    def api_call() -> tuple[dict[str, Any] | list[dict[str, Any]], dict[str, Any]]:
        """Get user information.

        Returns:
            The user information as a dictionary.

        """
        with Gitea(token=token, base_url=base_url) as client:
            return client.issue.edit_issue(
                owner=owner,
                repository=repository,
                index=index,
                assignee=assignee,
                assignees=assignees,
                body=body,
                due_date=due_date,
                milestone=milestone,
                ref=ref,
                state=state,
                title=title,
                unset_due_date=unset_due_date,
            )

    execute_api_command(api_call=api_call, command_name="gitea-cli issue edit")
