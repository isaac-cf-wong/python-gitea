"""Unit tests for the paginated-listing helpers."""

import pytest

from gitea.utils.pagination import collect_all_pages, iter_async_pages, iter_pages


def make_fetch_page(pages, requested=None):
    """Build a page fetcher serving one page per requested page number.

    Args:
        pages: The items of each page, in order.
        requested: List recording the page numbers requested, if given.

    Returns:
        A callable returning the requested page, or an empty page beyond the last one.

    """

    def fetch_page(page):
        if requested is not None:
            requested.append(page)
        return (list(pages[page - 1]) if page <= len(pages) else [], {"status_code": 200, "page": page})

    return fetch_page


def test_collect_all_pages_measures_short_pages_against_the_first_page():
    """A page longer than the first must not make the pages after it look terminal."""
    pages = [
        [{"id": 1}, {"id": 2}],
        [{"id": 3}, {"id": 4}, {"id": 5}],
        [{"id": 6}, {"id": 7}],
        [{"id": 8}],
    ]
    requested: list[int] = []

    items, metadata = collect_all_pages(make_fetch_page(pages, requested))

    assert [item["id"] for item in items] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert requested == [1, 2, 3, 4]
    assert metadata == {"status_code": 200, "page": 4}


def test_collect_all_pages_stops_on_an_empty_first_page():
    """A listing with nothing in it should cost one request."""
    requested: list[int] = []

    items, metadata = collect_all_pages(make_fetch_page([[]], requested))

    assert items == []
    assert requested == [1]
    assert metadata == {"status_code": 200, "page": 1}


def test_iter_pages_requests_pages_lazily():
    """A caller that stops early should stop the requests with it."""
    pages = [[{"id": 1}, {"id": 2}], [{"id": 3}, {"id": 4}], [{"id": 5}]]
    requested: list[int] = []

    for batch, _ in iter_pages(make_fetch_page(pages, requested)):
        if any(item["id"] == 3 for item in batch):
            break

    assert requested == [1, 2]


def make_async_fetch_page(pages, requested=None):
    """Build an awaitable page fetcher serving one page per requested page number.

    Args:
        pages: The items of each page, in order.
        requested: List recording the page numbers requested, if given.

    Returns:
        A coroutine function returning the requested page, or an empty page
        beyond the last one.

    """
    fetch_page = make_fetch_page(pages, requested)

    async def fetch_page_async(page):
        return fetch_page(page)

    return fetch_page_async


@pytest.mark.asyncio
async def test_iter_async_pages_measures_short_pages_against_the_first_page():
    """A page longer than the first must not make the pages after it look terminal."""
    pages = [
        [{"id": 1}, {"id": 2}],
        [{"id": 3}, {"id": 4}, {"id": 5}],
        [{"id": 6}, {"id": 7}],
        [{"id": 8}],
    ]
    requested: list[int] = []

    seen = [batch async for batch, _ in iter_async_pages(make_async_fetch_page(pages, requested))]

    assert [item["id"] for batch in seen for item in batch] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert requested == [1, 2, 3, 4]


@pytest.mark.asyncio
async def test_iter_async_pages_stops_on_an_empty_first_page():
    """A listing with nothing in it should cost one request."""
    requested: list[int] = []

    seen = [batch async for batch, _ in iter_async_pages(make_async_fetch_page([[]], requested))]

    assert seen == [[]]
    assert requested == [1]


@pytest.mark.asyncio
async def test_iter_async_pages_requests_pages_lazily():
    """A caller that stops early should stop the requests with it."""
    pages = [[{"id": 1}, {"id": 2}], [{"id": 3}, {"id": 4}], [{"id": 5}]]
    requested: list[int] = []

    async for batch, _ in iter_async_pages(make_async_fetch_page(pages, requested)):
        if any(item["id"] == 3 for item in batch):
            break

    assert requested == [1, 2]


@pytest.mark.asyncio
async def test_iter_async_pages_yields_the_metadata_of_each_page():
    """The metadata of a page should be yielded alongside its items.

    Pages of equal length cannot be told apart from a last one, so the listing
    is followed by the empty page that ends it.
    """
    seen = [metadata async for _, metadata in iter_async_pages(make_async_fetch_page([[{"id": 1}], [{"id": 2}]]))]

    assert [metadata["page"] for metadata in seen] == [1, 2, 3]
    assert all(metadata["status_code"] == 200 for metadata in seen)
