"""Errors raised by the CLI itself rather than by the HTTP layer."""

from __future__ import annotations


class CommandError(Exception):
    """A command failed for a reason the user can act on.

    `execute_api_command` reports these without a traceback, so the message is
    the whole error the user sees: state what went wrong and what to do next.
    """
