# ruff: noqa PLC0415
"""Main entry point for the python-gitea CLI application."""

from __future__ import annotations

import enum
from typing import Annotated

import typer

from pathlib import Path


class LoggingLevel(str, enum.Enum):
    """Logging levels for the CLI."""

    NOTSET = "NOTSET"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# Create the main Typer app
app = typer.Typer(
    name="python-gitea",
    help="Main CLI for python-gitea.",
    rich_markup_mode="rich",
)


def setup_logging(level: LoggingLevel = LoggingLevel.INFO) -> None:
    """Set up logging with Rich handler.

    Args:
        level: Logging level.
    """
    import logging

    from rich.console import Console
    from rich.logging import RichHandler

    logger = logging.getLogger("python-gitea")

    logger.setLevel(level.value)

    console = Console()

    # Remove any existing handlers to ensure RichHandler is used
    for h in logger.handlers[:]:  # Use slice copy to avoid modification during iteration
        logger.removeHandler(h)
    # Add the RichHandler

    handler = RichHandler(
        console=console,
        rich_tracebacks=True,
        show_time=True,
        show_level=True,  # Keep level (e.g., DEBUG, INFO) for clarity
        markup=True,  # Enable Rich markup in messages for styling
        level=level.value,  # Ensure handler respects the level
        omit_repeated_times=False,
        log_time_format="%H:%M",
    )
    handler.setLevel(level.value)
    logger.addHandler(handler)

    # Prevent propagation to root logger to avoid duplicate output
    logger.propagate = False


@app.callback()
def main(
    ctx: typer.Context,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output file name.")] = None,
    token: Annotated[
        str | None, typer.Option("--token", "-t", help="Gitea API token.", envvar="GITEA_API_TOKEN")
    ] = None,
    base_url: Annotated[
        str,
        typer.Option(
            "--base-url",
            "-b",
            help="Base URL of the Gitea instance.",
            envvar="GITEA_BASE_URL",
            show_default=True,
        ),
    ] = "https://gitea.com",
    verbose: Annotated[
        LoggingLevel,
        typer.Option("--verbose", "-v", help="Set verbosity level."),
    ] = LoggingLevel.INFO,
) -> None:
    """Main entry point for the CLI application.

    Args:
        ctx: Typer context.
        token: Gitea API token.
        base_url: Base URL of the Gitea instance.
        verbose: Verbosity level for logging.
    """
    setup_logging(verbose)
    ctx.obj = {
        "output": output,
        "token": token,
        "base_url": base_url,
    }


def register_commands() -> None:
    """Register CLI commands."""
    from gitea.cli.user.main import user_app

    app.add_typer(user_app, name="user", help="Commands for managing Gitea users.")


register_commands()
