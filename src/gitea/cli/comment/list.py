"""List comments command."""

from __future__ import annotations

from typing import Annotated

import typer


def list_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    repository: Annotated[str, typer.Option("--repository", help="Name of the repository.")],
    index: Annotated[int, typer.Option("--index", help="Index of the issue.")],
    page: Annotated[
        int | None,
        typer.Option("--page", help="The page number for pagination."),
    ] = None,
    limit: Annotated[
        int | None,
        typer.Option("--limit", help="The number of comments per page."),
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
    """List comments on an issue.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository.
        index: The index of the issue.
        page: The page number for pagination.
        limit: The number of comments per page.
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
        """List comment information.

        Returns:
            A tuple containing the comment data and metadata.

        """
        with Gitea(token=token, base_url=base_url) as client:
            return client.comment.list_comments(
                owner=owner,
                repository=repository,
                index=index,
                page=page,
                limit=limit,
            )

    execute_api_command(api_call=api_call, base_url=base_url, command_name="gitea-cli comment list")
