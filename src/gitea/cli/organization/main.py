"""CLI commands for managing organizations."""

from __future__ import annotations

import typer

organization_app = typer.Typer(
    name="org",
    help="Commands for managing organizations.",
    rich_markup_mode="rich",
)


def register_commands() -> None:
    """Register organization-related commands to the organization_app."""
    from gitea.cli.organization.list import list_command  # noqa: PLC0415

    organization_app.command("list", help="List organizations.")(list_command)


register_commands()
