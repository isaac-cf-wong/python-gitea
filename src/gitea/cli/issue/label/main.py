"""CLI commands for managing the labels of issues."""

from __future__ import annotations

import typer

label_app = typer.Typer(
    name="label",
    help="Commands for managing the labels of issues.",
    rich_markup_mode="rich",
)


def register_commands() -> None:
    """Register issue-label commands to the label_app."""
    from gitea.cli.issue.label.add import add_command  # noqa: PLC0415
    from gitea.cli.issue.label.clear import clear_command  # noqa: PLC0415
    from gitea.cli.issue.label.list import list_command  # noqa: PLC0415
    from gitea.cli.issue.label.remove import remove_command  # noqa: PLC0415
    from gitea.cli.issue.label.set import set_command  # noqa: PLC0415

    label_app.command("add", help="Add labels to issues, keeping the labels they already have.")(add_command)
    label_app.command("clear", help="Remove every label from issues.")(clear_command)
    label_app.command("list", help="List the labels of issues.")(list_command)
    label_app.command("remove", help="Remove labels from issues.")(remove_command)
    label_app.command("set", help="Replace every label of issues with the given labels.")(set_command)


register_commands()
