"""CLI commands for managing labels."""

from __future__ import annotations

import typer

label_app = typer.Typer(
    name="label",
    help="Commands for managing labels.",
    rich_markup_mode="rich",
)


def register_commands() -> None:
    """Register label-related commands to the label_app."""
    from gitea.cli.label.create import create_command  # noqa: PLC0415
    from gitea.cli.label.delete import delete_command  # noqa: PLC0415
    from gitea.cli.label.list import list_command  # noqa: PLC0415
    from gitea.cli.label.update import update_command  # noqa: PLC0415

    label_app.command("create", help="Create a label.")(create_command)
    label_app.command("delete", help="Delete a label.")(delete_command)
    label_app.command("list", help="List labels.")(list_command)
    label_app.command("update", help="Update a label.")(update_command)


register_commands()
