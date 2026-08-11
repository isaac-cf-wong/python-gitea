"""Create issues command."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

import typer


def create_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    repository: Annotated[str, typer.Option("--repository", help="Name of the repository.")],
    title: Annotated[str, typer.Option("--title", help="Title of the new issue.")],
    assignee: Annotated[
        str | None,
        typer.Option("--assignee", help="The username to assign the issue to."),
    ] = None,
    assignees: Annotated[
        list[str] | None,
        typer.Option("--assignees", help="The usernames to assign the issue to."),
    ] = None,
    body: Annotated[
        str | None,
        typer.Option("--body", help="The body of the new issue."),
    ] = None,
    closed: Annotated[
        bool | None,
        typer.Option("--closed", help="Whether the issue is created closed."),
    ] = None,
    due_date: Annotated[
        datetime | None,
        typer.Option("--due-date", help="The due date of the new issue."),
    ] = None,
    labels: Annotated[
        list[int] | None,
        typer.Option("--labels", help="The label IDs to apply to the new issue."),
    ] = None,
    milestone: Annotated[
        int | None,
        typer.Option("--milestone", help="The milestone ID to associate with the new issue."),
    ] = None,
    ref: Annotated[
        str | None,
        typer.Option("--ref", help="The reference of the new issue."),
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
    """Create a new issue in a repository.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository.
        title: The title of the new issue.
        assignee: The username to assign the issue to.
        assignees: The usernames to assign the issue to.
        body: The body of the new issue.
        closed: Whether the issue is created closed.
        due_date: The due date of the new issue.
        labels: The label IDs to apply to the new issue.
        milestone: The milestone ID to associate with the new issue.
        ref: The reference of the new issue.
        account_name: Name of the account to use for authentication.
        token: Token for authentication.
        base_url: Base URL of the Gitea platform.

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
        """Create issue information.

        Returns:
            A tuple containing the issue data and metadata.

        """
        with Gitea(token=token, base_url=base_url) as client:
            return client.issue.create_issue(
                owner=owner,
                repository=repository,
                title=title,
                assignee=assignee,
                assignees=assignees,
                body=body,
                closed=closed,
                due_date=due_date,
                labels=labels,
                milestone=milestone,
                ref=ref,
            )

    execute_api_command(api_call=api_call, command_name="gitea-cli issue create")
