"""CLI commands for managing issue dependencies."""

from __future__ import annotations

import typer

dependency_app = typer.Typer(
    name="dependency",
    help="Commands for managing issue dependencies.",
    rich_markup_mode="rich",
)


def register_commands() -> None:
    """Register dependency-related commands to the dependency_app."""
    from gitea.cli.issue.dependency.add import add_command  # noqa: PLC0415
    from gitea.cli.issue.dependency.list import list_command  # noqa: PLC0415
    from gitea.cli.issue.dependency.remove import remove_command  # noqa: PLC0415

    dependency_app.command("add", help="Make an issue depend on another issue.")(add_command)
    dependency_app.command("list", help="List an issue's dependencies.")(list_command)
    dependency_app.command("remove", help="Remove an issue dependency.")(remove_command)


register_commands()
