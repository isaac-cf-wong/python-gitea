"""Utility functions for processing HTTP responses."""

from __future__ import annotations

from typing import Any

from aiohttp import ClientResponse
from requests import Response


def process_response(response: Response) -> tuple[dict[str, Any] | list[dict[str, Any]], int]:
    """Process a synchronous HTTP response.

    Args:
        response: The HTTP response object.

    Returns:
        A tuple containing the response data and status code.
    """
    status_code = response.status_code
    data = response.json() if status_code == 200 else {}  # noqa: PLR2004
    return data, status_code


async def process_async_response(response: ClientResponse) -> tuple[dict[str, Any] | list[dict[str, Any]], int]:
    """Process an asynchronous HTTP response.

    Args:
        response: The asynchronous HTTP response object.

    Returns:
        A tuple containing the response data and status code.
    """
    status_code = response.status
    data = await response.json() if status_code == 200 else {}  # noqa: PLR2004
    return data, status_code
