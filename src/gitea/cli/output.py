"""Utilities for selecting and rendering the CLI output format.

This lives outside `gitea.cli.utils` on purpose: `main.py` needs `OutputFormat`
at import time to declare the global `--output` option, and importing it from
`gitea.cli.utils` would pull that package's configuration and API helpers - and
so pydantic and YAML - into the startup path of every invocation.
"""

from __future__ import annotations

import enum
import json
from collections.abc import Callable
from typing import Any

import typer


class OutputFormat(enum.StrEnum):
    """Output formats accepted by the global `--output` option."""

    TEXT = "text"
    JSON = "json"


def get_output_format(ctx: typer.Context) -> OutputFormat:
    """Get the output format requested for the current invocation.

    Args:
        ctx: Typer context carrying the state set by the root callback.

    Returns:
        The requested output format, defaulting to `OutputFormat.TEXT`.

    """
    return (ctx.obj or {}).get("output", OutputFormat.TEXT)


def print_envelope(data: Any, metadata: dict[str, Any]) -> None:
    """Print a result as the `{"data": ..., "metadata": ...}` JSON envelope.

    Args:
        data: Payload of the command.
        metadata: Information about the call that produced the payload.

    """
    print(json.dumps({"data": data, "metadata": metadata}, indent=2, default=str))


def emit(
    ctx: typer.Context,
    *,
    data: Any,
    metadata: dict[str, Any],
    render_text: Callable[[], None] | None = None,
) -> None:
    """Emit a command result in the format requested for this invocation.

    Args:
        ctx: Typer context carrying the state set by the root callback.
        data: Payload of the command, used for the JSON envelope.
        metadata: Information about the call, used for the JSON envelope.
        render_text: Callable printing the human-readable rendering. When
            omitted, the command prints nothing on stdout in text mode.

    """
    if get_output_format(ctx) is OutputFormat.JSON:
        print_envelope(data=data, metadata=metadata)
    elif render_text is not None:
        render_text()
