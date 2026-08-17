"""CLI commands for managing issues."""

from __future__ import annotations

import typer

issue_app = typer.Typer(
    name="issue",
    help="Commands for managing issues.",
    rich_markup_mode="rich",
)


def register_commands() -> None:
    """Register issue-related commands to the issue_app."""
    from gitea.cli.comment.main import comment_app  # noqa: PLC0415
    from gitea.cli.issue.close import close_command  # noqa: PLC0415
    from gitea.cli.issue.create import create_command  # noqa: PLC0415
    from gitea.cli.issue.dependency.main import dependency_app  # noqa: PLC0415
    from gitea.cli.issue.edit import edit_command  # noqa: PLC0415
    from gitea.cli.issue.get import get_command  # noqa: PLC0415
    from gitea.cli.issue.list import list_command  # noqa: PLC0415

    issue_app.command("close", help="Close an issue.")(close_command)
    issue_app.command("create", help="Create an issue.")(create_command)
    issue_app.command("edit", help="Edit an issue.")(edit_command)
    issue_app.command("get", help="Get an issue.")(get_command)
    issue_app.command("list", help="List issues.")(list_command)
    issue_app.add_typer(dependency_app, name="dependency", help="Commands for managing issue dependencies.")
    # Alias of the top-level `comment` app: agents and users naturally look for
    # comment commands under `issue`. Both entry points share the same commands.
    issue_app.add_typer(comment_app, name="comment", help="Commands for managing comments.")


register_commands()
