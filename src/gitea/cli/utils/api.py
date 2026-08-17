"""Utility functions for calling API."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import typer

from gitea.cli.output import print_envelope

logger = logging.getLogger("gitea")


def execute_api_command(
    api_call: Callable[[], tuple[dict[str, Any] | list[dict[str, Any]], dict[str, Any]]],
    command_name: str = "Command",
) -> None:
    """Execute an API command and output results.

    The result is always written as the `{"data": ..., "metadata": ...}` JSON
    envelope, so these commands already satisfy `--output json` and are
    unaffected by `--output text`.

    Args:
        api_call: Callable that executes the API call and returns the result.
        command_name: Name of the command for error messages.

    """
    try:
        response_data, metadata = api_call()

        print_envelope(data=response_data, metadata=metadata)
    except Exception as e:
        logger.exception("Error executing %s", command_name)
        raise typer.Exit(1) from e
