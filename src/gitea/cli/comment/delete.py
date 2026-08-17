"""Delete comment command."""

from __future__ import annotations

from typing import Annotated

import typer


def delete_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    repository: Annotated[str, typer.Option("--repository", help="Name of the repository.")],
    comment_id: Annotated[int, typer.Option("--comment-id", help="ID of the comment.")],
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
    """Delete a comment.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository.
        comment_id: The ID of the comment.
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
        """Delete comment information.

        Returns:
            A tuple containing the comment data and metadata.

        """
        with Gitea(token=token, base_url=base_url) as client:
            return client.comment.delete_comment(
                owner=owner,
                repository=repository,
                comment_id=comment_id,
            )

    execute_api_command(api_call=api_call, base_url=base_url, command_name="gitea-cli comment delete")
