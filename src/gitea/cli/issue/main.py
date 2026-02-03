"""CLI commands for managing Gitea issues."""

from __future__ import annotations

import typer

issue_app = typer.Typer(
    name="issue",
    help="Commands for managing issues.",
    rich_markup_mode="rich",
)


def register_commands() -> None:
    """Register user-related commands to the user_app."""


register_commands()
