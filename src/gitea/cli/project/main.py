"""CLI commands for managing projects."""

from __future__ import annotations

import typer

project_app = typer.Typer(
    name="project",
    help="Commands for managing projects.",
    rich_markup_mode="rich",
)

column_app = typer.Typer(
    name="column",
    help="Commands for managing project columns.",
    rich_markup_mode="rich",
)


def register_commands() -> None:
    """Register project-related commands to the project_app."""
    from gitea.cli.project.column.create import create_column_command  # noqa: PLC0415
    from gitea.cli.project.column.list import list_columns_command  # noqa: PLC0415
    from gitea.cli.project.create import create_command  # noqa: PLC0415
    from gitea.cli.project.delete import delete_command  # noqa: PLC0415
    from gitea.cli.project.edit import edit_command  # noqa: PLC0415
    from gitea.cli.project.get import get_command  # noqa: PLC0415
    from gitea.cli.project.issue.add import add_issue_command  # noqa: PLC0415
    from gitea.cli.project.issue.move import move_issue_command  # noqa: PLC0415
    from gitea.cli.project.issue.remove import remove_issue_command  # noqa: PLC0415
    from gitea.cli.project.list import list_command  # noqa: PLC0415

    project_app.command("create", help="Create a project.")(create_command)
    project_app.command("list", help="List projects.")(list_command)
    project_app.command("get", help="Get a project.")(get_command)
    project_app.command("edit", help="Edit a project.")(edit_command)
    project_app.command("delete", help="Delete a project.")(delete_command)

    column_app.command("create", help="Create a column in a project.")(create_column_command)
    column_app.command("list", help="List a project's columns.")(list_columns_command)

    project_app.add_typer(column_app, name="column", help="Commands for managing project columns.")

    issue_app = typer.Typer(name="issue", help="Commands for managing project issues.", rich_markup_mode="rich")
    issue_app.command("add", help="Add an issue to a project column.")(add_issue_command)
    issue_app.command("move", help="Move an issue between a project's columns.")(move_issue_command)
    issue_app.command("remove", help="Remove an issue from a project column.")(remove_issue_command)
    project_app.add_typer(issue_app, name="issue", help="Commands for managing project issues.")


register_commands()
