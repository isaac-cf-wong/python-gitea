# ruff: noqa PLC0415

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
        status: The status to filter workflow jobs by. Options: pending, queued, in_progress, failure, success, skipped.
        page: The page number for pagination.
        limit: The number of items per page for pagination.
    """
    from gitea.client.gitea import Gitea
    from rich.console import Console
    import json
    from pathlib import Path

    output: Path | None = ctx.obj.get("output")
    token: str | None = ctx.obj.get("token")
    base_url: str = ctx.obj.get("base_url")

    with Gitea(token=token, base_url=base_url) as client:
        result = client.user.get_workflow_jobs(status=status, page=page, limit=limit)

    json_output = json.dumps(result, indent=4)

    console = Console()

    if output:
        output.write_text(json_output)
        console.print(f"Output saved to {output}")
    else:
        console.print_json(json_output)
