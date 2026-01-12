"""Get workflow runs command for Gitea CLI."""

from __future__ import annotations

from typing import Annotated, Literal

import typer


def get_workflow_runs_command(  # noqa: PLR0913
    ctx: typer.Context,
    event: Annotated[str | None, typer.Option("--event", help="Workflow event name.")] = None,
    branch: Annotated[str | None, typer.Option("--branch", help="Workflow branch.")] = None,
    status: Annotated[
        Literal["pending", "queued", "in_progress", "failure", "success", "skipped"] | None,
        typer.Option(
            "--status",
            help="Workflow status.",
        ),
    ] = None,
    actor: Annotated[str | None, typer.Option("--actor", help="Triggered by user.")] = None,
    head_sha: Annotated[str | None, typer.Option("--head-sha", help="Triggering sha of the workflow run.")] = None,
    page: Annotated[int | None, typer.Option("--page", help="Page number of results to return.")] = None,
    limit: Annotated[int | None, typer.Option("--limit", help="Page size of results.")] = None,
) -> None:
    """Get workflow runs for the authenticated user filtered by various parameters.

    Args:
        event: The event that triggered the workflow run.
        branch: The branch name to filter workflow runs.
        status: The status to filter workflow jobs by. Options: pending, queued, in_progress, failure, success, skipped.
        actor: The actor who triggered the workflow run.
        head_sha: The head SHA to filter workflow runs.
        page: The page number for pagination.
        limit: The number of items per page for pagination.
    """
    from typing import Any  # noqa: PLC0415

    from gitea.cli.utils import execute_api_command  # noqa: PLC0415
    from gitea.client.gitea import Gitea  # noqa: PLC0415

    token: str | None = ctx.obj.get("token")
    base_url: str = ctx.obj.get("base_url")
    timeout: int = ctx.obj.get("timeout")

    def api_call() -> dict[str, Any] | None:
        """API call to get workflow runs.

        Returns:
            A dictionary containing the workflow runs.
        """
        with Gitea(token=token, base_url=base_url) as client:
            return client.user.get_workflow_runs(
                event=event,
                branch=branch,
                status=status,
                actor=actor,
                head_sha=head_sha,
                page=page,
                limit=limit,
                timeout=timeout,
            )

    execute_api_command(ctx=ctx, api_call=api_call, command_name="get-workflow-runs")
