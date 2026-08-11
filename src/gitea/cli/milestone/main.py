"""CLI commands for managing milestones."""

from __future__ import annotations

import typer

milestone_app = typer.Typer(
    name="milestone",
    help="Commands for managing milestones.",
    rich_markup_mode="rich",
)


def register_commands() -> None:
    """Register milestone-related commands to the milestone_app."""
    from gitea.cli.milestone.create import create_command  # noqa: PLC0415
    from gitea.cli.milestone.list import list_command  # noqa: PLC0415

    milestone_app.command("create", help="Create a milestone.")(create_command)
    milestone_app.command("list", help="List milestones.")(list_command)


register_commands()
