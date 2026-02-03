"""Main entry point for the python-gitea CLI application."""

from __future__ import annotations

import enum
from typing import Annotated

import typer


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
    import logging  # noqa: PLC0415

    from rich.console import Console  # noqa: PLC0415
    from rich.logging import RichHandler  # noqa: PLC0415

    logger = logging.getLogger("gitea")

    logger.setLevel(level.value)

    console = Console(stderr=True)

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
    config_path: Annotated[
        str | None,
        typer.Option(
            "--config-path",
            help="Path to the configuration file. If not provided, it uses the path specified by `GITEA_CONFIG_PATH`. If the environment variable is not defined, it uses the default location.",
        ),
    ] = None,
    verbose: Annotated[
        LoggingLevel,
        typer.Option("--verbose", "-v", help="Set verbosity level."),
    ] = LoggingLevel.INFO,
) -> None:
    """Enter the CLI application.

    Args:
        ctx: Typer context.
        config_path: Path to the configuration file.
        verbose: Verbosity level for logging.

    """
    import os  # noqa: PLC0415

    config_path = config_path or os.getenv("PYTHON_GITEA_CONFIG_PATH")

    ctx.obj = {"config_path": config_path}
    setup_logging(verbose)


def register_commands() -> None:
    """Register CLI commands."""
    from gitea.cli.config.main import config_app  # noqa: PLC0415
    from gitea.cli.issue.main import issue_app  # noqa: PLC0415
    from gitea.cli.pull_request.main import pull_request_app  # noqa: PLC0415
    from gitea.cli.user.main import user_app  # noqa: PLC0415

    app.add_typer(config_app, name="config", help="Commands for managing configurations.")
    app.add_typer(issue_app, name="issue", help="Commands for managing issues.")
    app.add_typer(pull_request_app, name="pull-request", help="Commands for managing pull requests.")
    app.add_typer(user_app, name="user", help="Commands for managing users.")


register_commands()
