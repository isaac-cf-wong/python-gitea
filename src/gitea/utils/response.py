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


def process_text_response(response: Response, default: str = "") -> tuple[str, int]:
    """Process a synchronous HTTP response whose body is text rather than JSON.

    A few endpoints answer with a file rather than with a document - the logs of
    an Actions job are the log itself - so there is nothing to parse and nothing
    to fall back to when parsing fails.

    The body is decoded as UTF-8 rather than through `response.text`, which
    guesses the encoding when the response declares none: a log blob served as
    `application/octet-stream` would be decoded by that guess, and the same
    bytes would then reach a caller differently depending on what the guess
    was. Gitea writes these as UTF-8, and the asynchronous path decodes them the
    same way, so both clients hand back the same text. A byte that is not valid
    UTF-8 is replaced rather than raising, since a log is worth reading even
    where one line of it is malformed.

    Args:
        response: The HTTP response object.
        default: The value to return when the response carries no body.

    Returns:
        A tuple containing the response text and status code.

    """
    status_code = response.status_code
    if 200 <= status_code < 300 and response.content:  # noqa: PLR2004
        return response.content.decode("utf-8", errors="replace"), cast(int, status_code)
    return default, cast(int, status_code)


async def process_async_text_response(response: ClientResponse, default: str = "") -> tuple[str, int]:
    """Process an asynchronous HTTP response whose body is text rather than JSON.

    Decoded as `process_text_response` decodes it, so a caller reading the logs
    of a job gets the same text from either client.

    Args:
        response: The asynchronous HTTP response object.
        default: The value to return when the response carries no body.

    Returns:
        A tuple containing the response text and status code.

    """
    status_code = response.status
    if 200 <= status_code < 300:  # noqa: PLR2004
        body = await response.read()
        if body:
            return body.decode("utf-8", errors="replace"), status_code
    return default, status_code


def process_binary_response(response: Response, default: bytes = b"") -> tuple[bytes, int]:
    """Process a synchronous HTTP response whose body is a file rather than a document.

    An Actions artifact is a zip archive, so there is nothing to parse and
    nothing to decode: handing back the bytes is the whole of it. Decoding them
    as text - as the log endpoints are decoded - would replace every byte that is
    not valid UTF-8 and produce an archive that no longer opens, which is why
    this exists alongside `process_text_response` rather than reusing it.

    Args:
        response: The HTTP response object.
        default: The value to return when the response carries no body.

    Returns:
        A tuple containing the response body and status code.

    """
    status_code = response.status_code
    if 200 <= status_code < 300 and response.content:  # noqa: PLR2004
        return response.content, cast(int, status_code)
    return default, cast(int, status_code)


async def process_async_binary_response(response: ClientResponse, default: bytes = b"") -> tuple[bytes, int]:
    """Process an asynchronous HTTP response whose body is a file rather than a document.

    Handed back as `process_binary_response` hands it back, so an artifact
    downloaded through either client is the same archive.

    Args:
        response: The asynchronous HTTP response object.
        default: The value to return when the response carries no body.

    Returns:
        A tuple containing the response body and status code.

    """
    status_code = response.status
    if 200 <= status_code < 300:  # noqa: PLR2004
        body = await response.read()
        if body:
            return body, status_code
    return default, status_code
