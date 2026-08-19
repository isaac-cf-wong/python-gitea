"""CLI commands for managing repositories."""

from __future__ import annotations

import typer

repository_app = typer.Typer(
    name="repo",
    help="Commands for managing repositories.",
    rich_markup_mode="rich",
)


def register_commands() -> None:
    """Register repository-related commands to the repository_app."""
    from gitea.cli.repository.list import list_command  # noqa: PLC0415

    repository_app.command("list", help="List repositories of an owner.")(list_command)


register_commands()
