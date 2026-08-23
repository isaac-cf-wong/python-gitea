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
    from gitea.cli.watch.advance import advance_command  # noqa: PLC0415
    from gitea.cli.watch.list import list_command  # noqa: PLC0415

    watch_app.command(
        "list",
        help=(
            "Report the issues that changed since the last run, and record the current state. Pass --no-advance "
            "to report them without recording, so they come back until 'watch advance' commits them."
        ),
    )(list_command)
    watch_app.command(
        "advance",
        help=(
            "Record the current state as the baseline to compare against, without reporting what changed. The "
            "counterpart of 'watch list --no-advance', for a caller that commits the cache once it has acted."
        ),
    )(advance_command)


register_commands()
