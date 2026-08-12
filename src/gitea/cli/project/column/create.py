"""Create project column command."""

from __future__ import annotations

from typing import Annotated

import typer


def create_column_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    project_id: Annotated[int, typer.Option("--project-id", help="ID of the project.")],
    title: Annotated[str, typer.Option("--title", help="Title of the column.")],
    color: Annotated[
        str | None,
        typer.Option("--color", help="Color of the column in 6-digit hex format, e.g. #FF0000."),
    ] = None,
    repository: Annotated[
        str | None,
        typer.Option("--repository", help="Name of the repository. Omit for organization projects."),
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
    """Create a column in a project.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository, or None for organization projects.
        project_id: The ID of the project.
        title: The title of the column.
        color: The color of the column in 6-digit hex format.
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
        """Create project column information.

        Returns:
            A tuple containing the column data and metadata.

        """
        with Gitea(token=token, base_url=base_url) as client:
            return client.project.create_project_column(
                owner=owner,
                repository=repository,
                project_id=project_id,
                title=title,
                color=color,
            )

    execute_api_command(api_call=api_call, command_name="gitea-cli project column create")
