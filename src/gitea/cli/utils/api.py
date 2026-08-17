"""Utility functions for calling API."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import requests
import typer

from gitea.cli.output import print_envelope
from gitea.cli.utils.errors import CommandError, unreachable_message

logger = logging.getLogger("gitea")

# The handler configured in `setup_logging` reads Rich markup in log messages,
# and these messages carry text the CLI did not write: error strings from the
# HTTP layer and URLs the user passed. A base URL with an IPv6 host, say
# `http://[fe80::1]:3000`, parses as a style tag and makes the handler raise,
# so every error below is logged as literal text.
_AS_TEXT = {"markup": False}


def execute_api_command(
    api_call: Callable[[], tuple[dict[str, Any] | list[dict[str, Any]], dict[str, Any]]],
    command_name: str = "Command",
    base_url: str | None = None,
) -> None:
    """Execute an API command and print the result as the JSON envelope.

    The result is always written as the `{"data": ..., "metadata": ...}` JSON
    envelope, so these commands already satisfy `--output json` and are
    unaffected by `--output text`. A command with a human-readable rendering of
    its own calls `execute_api_call` instead, and reports the result itself.

    Args:
        api_call: Callable that executes the API call and returns the result.
        command_name: Name of the command for error messages.
        base_url: The base URL the call is made against, so an unreachable
            instance is reported by the host the command tried to reach. The
            callable holds the client, so the host is not recoverable from here
            and every command is expected to pass it.

    """
    execute_api_call(
        api_call=api_call,
        report=lambda data, metadata: print_envelope(data=data, metadata=metadata),
        command_name=command_name,
        base_url=base_url,
    )


def execute_api_call(
    api_call: Callable[[], tuple[dict[str, Any] | list[dict[str, Any]], dict[str, Any]]],
    report: Callable[[dict[str, Any] | list[dict[str, Any]], dict[str, Any]], None],
    command_name: str = "Command",
    base_url: str | None = None,
) -> None:
    """Execute an API call and report its result, or its failure, uniformly.

    How a failure is reported is what every command has to agree on, so it lives
    here rather than at each call site. A `CommandError` is reported as its
    message alone, without a traceback, since it describes something the user
    can fix. A connection or timeout failure is reported the same way: it means
    the instance was never reached, which is as much as a traceback would say.
    A failed command exits non-zero having printed nothing on stdout, so the
    reporting is only reached once the call has succeeded.

    Args:
        api_call: Callable that executes the API call and returns the result.
        report: Callable writing the result out, given the data and the
            metadata. It runs inside the same error handling, so a
            `CommandError` raised while reporting is reported like any other.
        command_name: Name of the command for error messages.
        base_url: The base URL the call is made against, so an unreachable
            instance is reported by the host the command tried to reach. The
            callable holds the client, so the host is not recoverable from here
            and every command is expected to pass it.

    """
    try:
        response_data, metadata = api_call()

        report(response_data, metadata)
    except CommandError as e:
        # The message is the whole error the user needs; a traceback would bury it.
        logger.error("%s", e, extra=_AS_TEXT)
        raise typer.Exit(1) from e
    except (requests.ConnectionError, requests.Timeout) as e:
        # Raised before any response exists, so there is no status to report.
        logger.error("%s", unreachable_message(e, base_url), extra=_AS_TEXT)
        raise typer.Exit(1) from e
    except Exception as e:
        logger.exception("Error executing %s", command_name)
        raise typer.Exit(1) from e
