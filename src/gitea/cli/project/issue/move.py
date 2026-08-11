"""Move project issue command."""

from __future__ import annotations

from typing import Annotated

import typer


def move_issue_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    repository: Annotated[str, typer.Option("--repository", help="Name of the repository.")],
    project_id: Annotated[int, typer.Option("--project-id", help="ID of the project.")],
    issue_id: Annotated[int, typer.Option("--issue-id", help="ID of the issue.")],
    column_id: Annotated[int, typer.Option("--column-id", help="Target column ID.")],
    sorting: Annotated[
        int | None,
        typer.Option("--sorting", help="Position within the column, ascending."),
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
    """Move an issue between a project's columns.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository.
        project_id: The ID of the project.
        issue_id: The ID of the issue.
        column_id: The target column ID.
        sorting: The position within the column, ascending.
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
        """Move project issue information.

        Returns:
            A tuple containing the response data and metadata.

        """
        with Gitea(token=token, base_url=base_url) as client:
            return client.project.move_project_issue(
                owner=owner,
                repository=repository,
                project_id=project_id,
                issue_id=issue_id,
                column_id=column_id,
                sorting=sorting,
            )

    execute_api_command(api_call=api_call, command_name="gitea-cli project issue move")
