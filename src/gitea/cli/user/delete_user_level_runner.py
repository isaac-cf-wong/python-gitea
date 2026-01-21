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
        ctx: The Typer context.
        runner_id: The ID of the runner to delete.

    """
    from typing import Any  # noqa: PLC0415

    import gitea.cli.utils  # noqa: PLC0415
    import gitea.client.gitea  # noqa: PLC0415

    token: str | None = ctx.obj.get("token")
    base_url: str = ctx.obj.get("base_url")
    timeout: int = ctx.obj.get("timeout")

    def api_call() -> dict[str, Any] | None:
        """Delete a user-level runner.

        Returns:
            A dictionary containing the result of the deletion.

        """
        with gitea.client.gitea.Gitea(token=token, base_url=base_url) as client:
            return client.user.delete_user_level_runner(runner_id=runner_id, timeout=timeout)

    gitea.cli.utils.execute_api_command(ctx=ctx, api_call=api_call, command_name="delete-user-level-runner")
