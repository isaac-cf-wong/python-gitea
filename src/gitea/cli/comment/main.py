"""CLI commands for managing comments."""

from __future__ import annotations

import typer

comment_app = typer.Typer(
    name="comment",
    help="Commands for managing comments.",
    rich_markup_mode="rich",
)


def register_commands() -> None:
    """Register comment-related commands to the comment_app."""
    from gitea.cli.comment.add import add_command  # noqa: PLC0415
    from gitea.cli.comment.delete import delete_command  # noqa: PLC0415
    from gitea.cli.comment.edit import edit_command  # noqa: PLC0415
    from gitea.cli.comment.list import list_command  # noqa: PLC0415

    comment_app.command("add", help="Add a comment to an issue.")(add_command)
    comment_app.command("delete", help="Delete a comment.")(delete_command)
    comment_app.command("edit", help="Edit a comment.")(edit_command)
    comment_app.command("list", help="List comments on an issue.")(list_command)


register_commands()
