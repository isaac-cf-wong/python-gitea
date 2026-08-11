"""Utility functions for processing HTTP responses."""

from __future__ import annotations

import json
import logging
from typing import Any, cast

from aiohttp import ClientResponse
from requests import Response

logger = logging.getLogger("gitea")


def process_response[T](response: Response, default: T | None = None) -> tuple[Any, int]:
    """Process a synchronous HTTP response.

    Args:
        response: The HTTP response object.
        default: The default value to return if parsing fails.

    Returns:
        A tuple containing the response data and status code.

    """
    status_code = response.status_code
    if status_code == 204:  # noqa: PLR2004
        data = default
    elif 200 <= status_code < 300:  # noqa: PLR2004
        if not response.content:
            data = default
        else:
            try:
                data = response.json()
            except ValueError as e:
                logger.error("Failed to parse JSON response: %s", e)
                data = default
    else:
        data = default
    return data, cast(int, status_code)


async def process_async_response[T](response: ClientResponse, default: T | None = None) -> tuple[Any, int]:
    """Process an asynchronous HTTP response.

    Args:
        response: The asynchronous HTTP response object.
        default: The default value to return if parsing fails.

    Returns:
        A tuple containing the response data and status code.

    """
    status_code = response.status
    if status_code == 204:  # noqa: PLR2004
        data = default
    elif 200 <= status_code < 300:  # noqa: PLR2004
        body = await response.read()
        if not body:
            data = default
        else:
            try:
                data = json.loads(body)
            except (ValueError, UnicodeDecodeError) as e:
                logger.error("Failed to parse JSON response: %s", e)
                data = default
    else:
        data = default
    return data, status_code
