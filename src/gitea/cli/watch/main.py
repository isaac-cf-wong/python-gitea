"""CLI commands for watching issues for changes."""

from __future__ import annotations

import typer

watch_app = typer.Typer(
    name="watch",
    help="Commands for watching issues for changes.",
    rich_markup_mode="rich",
)


def register_commands() -> None:
    """Register watch-related commands to the watch_app."""
    from gitea.cli.watch.list import list_command  # noqa: PLC0415

    watch_app.command("list", help="Report the issues that changed since the last run.")(list_command)


register_commands()
