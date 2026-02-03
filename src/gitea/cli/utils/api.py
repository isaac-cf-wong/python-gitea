"""Utility functions for calling API."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

import typer

logger = logging.getLogger("gitea")


def execute_api_command(
    api_call: Callable[[], tuple[dict[str, Any] | list[dict[str, Any]], dict[str, Any]]],
    command_name: str = "Command",
) -> None:
    """Execute an API command and output results.

    Args:
        api_call: Callable that executes the API call and returns the result.
        command_name: Name of the command for error messages.

    """
    try:
        response_data, metadata = api_call()

        print(json.dumps({"data": response_data, "metadata": metadata}, indent=2, default=str))
    except Exception as e:
        logger.exception("Error executing %s: %s", command_name, e)
        raise typer.Exit(1) from e
