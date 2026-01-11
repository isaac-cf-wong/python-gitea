# ruff: noqa PLC0415

"""CLI commands for managing Gitea users."""

from __future__ import annotations

import typer

user_app = typer.Typer(
    name="user",
    help="Commands for managing Gitea users.",
    rich_markup_mode="rich",
)


def register_commands() -> None:
    """Register user-related commands to the user_app."""

    from gitea.cli.user.get_user import get_user_command
    from gitea.cli.user.get_workflow_jobs import get_workflow_jobs_command

    user_app.command("get-user")(get_user_command)
    user_app.command("get-workflow-jobs")(get_workflow_jobs_command)


register_commands()
