"""Get workflow jobs command for Gitea CLI."""

from __future__ import annotations

from typing import Annotated, Literal

import typer


def get_workflow_jobs_command(
    ctx: typer.Context,
    status: Annotated[
        Literal["pending", "queued", "in_progress", "failure", "success", "skipped"],
        typer.Option(
            "--status",
            help="The status to filter workflow jobs by. Options: pending, queued, in_progress, failure, success, skipped.",
        ),
    ],
    page: Annotated[int | None, typer.Option("--page", help="The page number for pagination.")] = None,
    limit: Annotated[int | None, typer.Option("--limit", help="The number of items per page for pagination.")] = None,
) -> None:
    """Get workflow jobs for the authenticated user filtered by status.

    Args:
        ctx: The Typer context.
        status: The status to filter workflow jobs by. Options: pending, queued, in_progress, failure, success, skipped.
        page: The page number for pagination.
        limit: The number of items per page for pagination.

    """
    from typing import Any  # noqa: PLC0415

    import gitea.cli.utils  # noqa: PLC0415
    import gitea.client.gitea  # noqa: PLC0415

    token: str | None = ctx.obj.get("token")
    base_url: str = ctx.obj.get("base_url")
    timeout: int = ctx.obj.get("timeout")

    def api_call() -> dict[str, Any] | None:
        """Get workflow jobs.

        Returns:
            A dictionary containing the workflow jobs with the specified status.

        """
        with gitea.client.gitea.Gitea(token=token, base_url=base_url) as client:
            return client.user.get_workflow_jobs(status=status, page=page, limit=limit, timeout=timeout)

    gitea.cli.utils.execute_api_command(ctx=ctx, api_call=api_call, command_name="get-workflow-jobs")
