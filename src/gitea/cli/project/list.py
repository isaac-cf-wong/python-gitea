"""List projects command."""

from __future__ import annotations

from typing import Annotated, Literal

import typer


def list_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    repository: Annotated[
        str | None,
        typer.Option("--repository", help="Name of the repository. Omit for organization projects."),
    ] = None,
    state: Annotated[
        Literal["open", "closed", "all"] | None,
        typer.Option("--state", help="Filter projects by state."),
    ] = None,
    page: Annotated[
        int | None,
        typer.Option("--page", help="The page number for pagination."),
    ] = None,
    limit: Annotated[
        int | None,
        typer.Option("--limit", help="The number of projects per page."),
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
    """List projects in a repository.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository, or None for organization projects.
        state: Filter projects by state.
        page: The page number for pagination.
        limit: The number of projects per page.
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
        """List project information.

        Returns:
            A tuple containing the project data and metadata.

        """
        with Gitea(token=token, base_url=base_url) as client:
            return client.project.list_projects(
                owner=owner,
                repository=repository,
                state=state,
                page=page,
                limit=limit,
            )

    execute_api_command(api_call=api_call, command_name="gitea-cli project list")
