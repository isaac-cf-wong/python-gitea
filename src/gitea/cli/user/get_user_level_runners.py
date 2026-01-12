"""Get user-level runners command for Gitea CLI."""

from __future__ import annotations

from typing import Annotated

import typer


def get_user_level_runners_command(
    ctx: typer.Context,
    runner_id: Annotated[str | None, typer.Option("--runner-id", help="The ID of the runner to retrieve.")] = None,
) -> None:
    """Get user-level runners for the authenticated user."""
    from typing import Any  # noqa: PLC0415

    from gitea.cli.utils import execute_api_command  # noqa: PLC0415
    from gitea.client.gitea import Gitea  # noqa: PLC0415

    token: str | None = ctx.obj.get("token")
    base_url: str = ctx.obj.get("base_url")
    timeout: int = ctx.obj.get("timeout")

    def api_call() -> dict[str, Any]:
        """
        API call to get user-level runners.

        Returns:
            A dictionary containing the user-level runners.
        """
        with Gitea(token=token, base_url=base_url) as client:
            return client.user.get_user_level_runners(runner_id=runner_id, timeout=timeout)

    execute_api_command(ctx=ctx, api_call=api_call, command_name="get-user-level-runners")
