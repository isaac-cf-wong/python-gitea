# ruff: noqa PLC0415

"""Get registration token command for Gitea CLI."""

from __future__ import annotations


import typer


def get_registration_token_command(
    ctx: typer.Context,
) -> None:
    """Get registration token for the authenticated user."""
    import gitea.client.gitea
    from typing import Any

    from gitea.cli.utils import execute_api_command

    token: str | None = ctx.obj.get("token")
    base_url: str = ctx.obj.get("base_url")
    timeout: int = ctx.obj.get("timeout")

    def api_call() -> dict[str, Any]:
        """
        API call to get the registration token.

        Returns:
            A dictionary containing the registration token.
        """
        with gitea.client.gitea.Gitea(token=token, base_url=base_url) as client:
            return client.user.get_registration_token(timeout=timeout)

    execute_api_command(ctx=ctx, api_call=api_call, command_name="get-registration-token")
