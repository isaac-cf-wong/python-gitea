"""Edit issues command."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

import typer

from gitea.cli.utils.options import DEPRECATED_INDEX_HELP, ISSUE_ID_HELP, REPOSITORY_REQUIRED_HELP


def edit_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    repository: Annotated[str | None, typer.Option("--repository", help=REPOSITORY_REQUIRED_HELP)] = None,
    issue_id: Annotated[int | None, typer.Option("--issue-id", help=ISSUE_ID_HELP)] = None,
    index: Annotated[int | None, typer.Option("--index", help=DEPRECATED_INDEX_HELP, hidden=True)] = None,
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
            help="Base URL of the Gitea platform. If not provided, the base URL from the specified account will be used.",
        ),
    ] = None,
) -> None:
    """Edit a specific issue in a repository.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository, which this command requires.
        issue_id: The issue number shown in the web UI.
        index: The deprecated name of `issue_id`.
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
    from gitea.cli.utils.options import require_repository, resolve_issue_id  # noqa: PLC0415
    from gitea.client.gitea import Gitea  # noqa: PLC0415

    token, base_url = get_auth_params(
        config_path=ctx.obj.get("config_path"),
        account_name=account_name,
        token=token,
        base_url=base_url,
    )

    def api_call() -> tuple[dict[str, Any] | list[dict[str, Any]], dict[str, Any]]:
        """Edit issue information.

        Returns:
            A tuple containing the issue data and metadata.

        """
        target_repository = require_repository(repository, command="gitea-cli issue edit")
        target_issue = resolve_issue_id(issue_id=issue_id, index=index, command="gitea-cli issue edit")

        with Gitea(token=token, base_url=base_url) as client:
            return client.issue.edit_issue(
                owner=owner,
                repository=target_repository,
                index=target_issue,
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

    execute_api_command(api_call=api_call, base_url=base_url, command_name="gitea-cli issue edit")
