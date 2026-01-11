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


register_commands()
