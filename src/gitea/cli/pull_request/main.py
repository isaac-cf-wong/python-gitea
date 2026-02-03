"""CLI commands for managing pull requests."""

from __future__ import annotations

import typer

pull_request_app = typer.Typer(
    name="pull-request",
    help="Commands for managing pull requests.",
    rich_markup_mode="rich",
)


def register_commands() -> None:
    """Register pull-request-related commands to the pull_request_app."""
    from gitea.cli.pull_request.list import list_command  # noqa: PLC0415

    pull_request_app.command("list", help="List pull requests.")(list_command)


register_commands()
