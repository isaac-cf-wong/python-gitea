"""Get user information command for Gitea CLI."""

from __future__ import annotations

from typing import Annotated

import typer


def get_command(
    ctx: typer.Context,
    username: Annotated[
        str | None, "The username of the user to retrieve. If None, retrieves the authenticated user."
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
    """Get user information.

    Args:
        ctx: The Typer context.
        username: The username of the user to retrieve. If None, retrieves the authenticated user.
        account_name: Name of the account to use for authentication.
        token: Token for authentication. If not provided, the token from the specified account will be used.
        base_url: Base URL of the GitHub platform. If not provided, the base URL from the specified account will be used.

    """
    from typing import Any  # noqa: PLC0415

    from gitea.cli.utils.api import execute_api_command  # noqa: PLC0415
    from gitea.cli.utils.auth import get_auth_params  # noqa: PLC0415
    from gitea.client.gitea import Gitea  # noqa: PLC0415

    token, base_url = get_auth_params(
        config_path=ctx.obj["config_path"],
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
            return client.user.get_user(username=username)

    execute_api_command(api_call=api_call, command_name="gitea-cli user get")
