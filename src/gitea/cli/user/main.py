"""CLI commands for managing users."""

from __future__ import annotations

import typer

user_app = typer.Typer(
    name="user",
    help="Commands for managing users.",
    rich_markup_mode="rich",
)


def register_commands() -> None:
    """Register user-related commands to the user_app."""
    from gitea.cli.user.get import get_command  # noqa: PLC0415
    from gitea.cli.user.update_settings import update_settings_command  # noqa: PLC0415

    user_app.command("get", help="Get user information.")(get_command)
    user_app.command("update-settings", help="Update user settings.")(update_settings_command)


register_commands()
