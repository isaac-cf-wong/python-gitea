# ruff: noqa PLC0415

"""Get user information command for Gitea CLI."""

from __future__ import annotations

from typing import Annotated

import typer


def get_user_command(
    ctx: typer.Context,
    username: Annotated[
        str | None, "The username of the user to retrieve. If None, retrieves the authenticated user."
    ] = None,
) -> None:
    """Get user information.

    Args:
        username: The username of the user to retrieve. If None, retrieves the authenticated user.
    """
    from gitea.client.gitea import Gitea
    from typing import Any

    from gitea.cli.utility import execute_api_command

    token: str | None = ctx.obj.get("token")
    base_url: str = ctx.obj.get("base_url")
    timeout: int = ctx.obj.get("timeout")

    def api_call() -> dict[str, Any]:
        """API call to get user information.

        Returns:
            The user information as a dictionary.
        """
        with Gitea(token=token, base_url=base_url) as client:
            return client.user.get_user(username=username, timeout=timeout)

    execute_api_command(ctx=ctx, api_call=api_call, command_name="get-user")
