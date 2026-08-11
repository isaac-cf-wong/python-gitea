"""CLI commands for managing notifications."""

from __future__ import annotations

import typer

notification_app = typer.Typer(
    name="notification",
    help="Commands for managing notifications.",
    rich_markup_mode="rich",
)


def register_commands() -> None:
    """Register notification-related commands to the notification_app."""
    from gitea.cli.notification.list import list_command  # noqa: PLC0415
    from gitea.cli.notification.read import read_command  # noqa: PLC0415

    notification_app.command("list", help="List notifications.")(list_command)
    notification_app.command("read", help="Mark notifications as read.")(read_command)


register_commands()
