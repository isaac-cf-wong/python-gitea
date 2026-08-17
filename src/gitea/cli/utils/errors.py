"""Errors raised by the CLI itself rather than by the HTTP layer."""

from __future__ import annotations


class CommandError(Exception):
    """A command failed for a reason the user can act on.

    `execute_api_command` reports these without a traceback, so the message is
    the whole error the user sees: state what went wrong and what to do next.
    """


def unreachable_message(error: Exception, base_url: str | None = None) -> str:
    """Build the error message for a request that never reached the instance.

    A connection or timeout failure says nothing about the account, the
    repository or the issue, so the message points at the instance and the
    network instead of at whatever the command was trying to do.

    Args:
        error: The connection or timeout error raised by the HTTP layer.
        base_url: The base URL the call was made against, when it is known.

    Returns:
        The message describing the failure and how to act on it.

    """
    where = f" at {base_url}" if base_url else ""
    return (
        f"Could not reach the Gitea API{where}: {error}. "
        f"Check that the instance is up, that the base URL is right and that the network allows the connection."
    )


def request_failed_message(error: Exception, base_url: str | None = None) -> str:
    """Build the error message for a request that failed without reaching a response.

    A malformed base URL, a rejected redirect or a response body that could not
    be read is not the instance being unreachable, so the message claims only
    that the request did not complete. It names the error's type, since there is
    no traceback to read it from.

    Args:
        error: The request error raised by the HTTP layer.
        base_url: The base URL the call was made against, when it is known.

    Returns:
        The message describing the failure and how to act on it.

    """
    where = f" at {base_url}" if base_url else ""
    return (
        f"Could not complete the request to the Gitea API{where}: {type(error).__name__}: {error}. "
        f"Check that the base URL is a well-formed URL of a Gitea instance."
    )
