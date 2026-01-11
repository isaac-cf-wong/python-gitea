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
    from rich.console import Console
    import json
    from pathlib import Path

    output: Path | None = ctx.obj.get("output")
    token: str | None = ctx.obj.get("token")
    base_url: str = ctx.obj.get("base_url")

    with Gitea(token=token, base_url=base_url) as client:
        user_info = client.user.get_user(username=username)

    json_output = json.dumps(user_info, indent=4)

    console = Console()

    if output:
        output.write_text(json_output)
        console.print(f"Output saved to {output}")
    else:
        console.print_json(json_output)
