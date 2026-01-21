"""CLI utility functions."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import typer
from rich.console import Console


def execute_api_command(
    ctx: typer.Context,
    api_call: Callable[[], dict[str, Any] | None],
    command_name: str = "Command",
) -> None:
    """Execute an API command and output results.

    Args:
        ctx: Typer context containing token, base_url, and output.
        api_call: Callable that executes the API call and returns the result.
        command_name: Name of the command for error messages.

    """
    output: Path | None = ctx.obj.get("output")
    console = Console()

    try:
        result = api_call()

        if result is None:
            console.print(f"{command_name} executed successfully. No content returned.")
            return

        json_output = json.dumps(result, indent=4)

        if output:
            Path(output).write_text(json_output)
            console.print(f"Output saved to {output}")
        else:
            console.print_json(json_output)
    except Exception as e:
        console.print(f"Error executing {command_name}: {e}", style="red")
        raise typer.Exit(1) from e
