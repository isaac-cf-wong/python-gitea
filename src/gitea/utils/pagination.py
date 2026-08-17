"""Helpers for walking paginated Gitea listings."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable, Iterator

# Number of items requested per page when paging through a listing.
PAGE_SIZE = 50


def _is_last_page(batch: list[dict[str, Any]], page_size: int) -> bool:
    """Report whether a page is the last one of a listing.

    A page is the last one when it comes back empty or shorter than the first
    page. The page size is taken from the first page rather than from the
    requested limit, because a Gitea instance may cap the page size below it.
    Only the first page is used, so that a later page which happens to be
    longer cannot make the pages after it look terminal.

    Args:
        batch: The items of the page.
        page_size: The size of the first page, or 0 while it is still unknown.

    Returns:
        True when no page after this one needs to be requested.

    """
    return not batch or len(batch) < page_size


def iter_pages(
    fetch_page: Callable[[int], tuple[list[dict[str, Any]], dict[str, Any]]],
) -> Iterator[tuple[list[dict[str, Any]], dict[str, Any]]]:
    """Yield the pages of a paginated listing, one request at a time.

    Pages are requested lazily, so a caller that stops early stops the
    requests with it.

    Args:
        fetch_page: Callable returning the items and metadata of the given page number.

    Yields:
        A tuple containing the items and the metadata of each page, in order.

    """
    page = 1
    page_size = 0
    while True:
        batch, metadata = fetch_page(page)
        yield batch, metadata
        if _is_last_page(batch, page_size):
            return
        page_size = page_size or len(batch)
        page += 1


async def iter_async_pages(
    fetch_page: Callable[[int], Awaitable[tuple[list[dict[str, Any]], dict[str, Any]]]],
) -> AsyncIterator[tuple[list[dict[str, Any]], dict[str, Any]]]:
    """Yield the pages of a paginated listing, one request at a time.

    Args:
        fetch_page: Callable returning the items and metadata of the given page number.

    Yields:
        A tuple containing the items and the metadata of each page, in order.

    """
    page = 1
    page_size = 0
    while True:
        batch, metadata = await fetch_page(page)
        yield batch, metadata
        if _is_last_page(batch, page_size):
            return
        page_size = page_size or len(batch)
        page += 1


def collect_all_pages(
    fetch_page: Callable[[int], tuple[list[dict[str, Any]], dict[str, Any]]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch every page of a paginated listing.

    Args:
        fetch_page: Callable returning the items and metadata of the given page number.

    Returns:
        A tuple containing every item across all pages and the metadata of the last response.

    """
    items: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {}
    for batch, page_metadata in iter_pages(fetch_page):
        items.extend(batch)
        metadata = page_metadata
    return items, metadata
