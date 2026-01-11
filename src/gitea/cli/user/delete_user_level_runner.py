# ruff: noqa PLC0415

"""Delete user-level runner command for Gitea CLI."""

from __future__ import annotations


from typing import Annotated

import typer


def delete_user_level_runner_command(
    ctx: typer.Context,
    runner_id: Annotated[str, typer.Option("--runner-id", help="The ID of the runner to delete.")],
) -> None:
    """Delete a user-level runner for the authenticated user.

    Args:
        runner_id: The ID of the runner to delete.
    """
    from gitea.client.gitea import Gitea
    from typing import Any

    from gitea.cli.utils import execute_api_command

    token: str | None = ctx.obj.get("token")
    base_url: str = ctx.obj.get("base_url")
    timeout: int = ctx.obj.get("timeout")

    def api_call() -> dict[str, Any]:
        """
        API call to delete a user-level runner.

        Returns:
            A dictionary containing the result of the deletion.
        """
        with Gitea(token=token, base_url=base_url) as client:
            return client.user.delete_user_level_runner(runner_id=runner_id, timeout=timeout)

    execute_api_command(ctx=ctx, api_call=api_call, command_name="delete-user-level-runner")
