# ruff: noqa PLC0415

"""Get registration token command for Gitea CLI."""

from __future__ import annotations


import typer


def get_registration_token_command(
    ctx: typer.Context,
) -> None:
    """Get registration token for the authenticated user."""
    from gitea.client.gitea import Gitea
    from typing import Any

    from gitea.cli.utility import execute_api_command

    token: str | None = ctx.obj.get("token")
    base_url: str = ctx.obj.get("base_url")

    def api_call() -> dict[str, Any]:
        """
        API call to get user-level runners.

        Returns:
            A dictionary containing the user-level runners.
        """
        with Gitea(token=token, base_url=base_url) as client:
            return client.user.get_registration_token()

    execute_api_command(ctx=ctx, api_call=api_call, command_name="get-registration-token")
