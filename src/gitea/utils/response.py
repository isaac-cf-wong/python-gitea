"""Utility functions for processing HTTP responses."""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientResponse
from requests import Response

logger = logging.getLogger("gitea")


def process_response(response: Response) -> tuple[dict[str, Any] | list[dict[str, Any]], int]:
    """Process a synchronous HTTP response.

    Args:
        response: The HTTP response object.

    Returns:
        A tuple containing the response data and status code.
    """
    status_code = response.status_code
    if status_code == 204:  # noqa: PLR2004
        data = {}
    elif 200 <= status_code < 300:  # noqa: PLR2004
        try:
            data = response.json()
        except ValueError as e:
            logger.error("Failed to parse JSON response: %s", e)
            data = {}
    else:
        data = {}
    return data, status_code


async def process_async_response(response: ClientResponse) -> tuple[dict[str, Any] | list[dict[str, Any]], int]:
    """Process an asynchronous HTTP response.

    Args:
        response: The asynchronous HTTP response object.

    Returns:
        A tuple containing the response data and status code.
    """
    status_code = response.status
    if status_code == 204:  # noqa: PLR2004
        data = {}
    elif 200 <= status_code < 300:  # noqa: PLR2004
        try:
            data = await response.json()
        except ValueError as e:
            logger.error("Failed to parse JSON response: %s", e)
            data = {}
    else:
        data = {}
    return data, status_code
