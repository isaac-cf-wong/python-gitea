"""CLI commands for managing issues."""

from __future__ import annotations

import typer

issue_app = typer.Typer(
    name="issue",
    help="Commands for managing issues.",
    rich_markup_mode="rich",
)


def register_commands() -> None:
    """Register issue-related commands to the issue_app."""
    from gitea.cli.issue.edit import edit_command  # noqa: PLC0415
    from gitea.cli.issue.get import get_command  # noqa: PLC0415
    from gitea.cli.issue.list import list_command  # noqa: PLC0415

    issue_app.command("edit", help="Edit an issue.")(edit_command)
    issue_app.command("get", help="Get an issue.")(get_command)
    issue_app.command("list", help="List issues.")(list_command)


register_commands()
