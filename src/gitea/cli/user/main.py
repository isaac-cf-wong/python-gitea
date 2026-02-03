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

    user_app.command("get")(get_command)


register_commands()
