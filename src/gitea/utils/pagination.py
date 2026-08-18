"""Helpers for walking paginated Gitea listings.

A listing is walked by asking for page 1, then page 2, and so on until a page
says the listing has ended. What a page says is the whole difficulty: the
endpoints wrapped here return a bare JSON array, so "this was the last one" has
to be inferred, and an instance that infers wrongly is asked for page 3, page 4
and page 5 forever.

Four things end a walk.

* **The page repeats the one before it.** Checked first, and before the page is
  handed to the caller: an instance that ignores the `page` parameter answers
  every request with the same items, so no page is ever empty, short, or
  different from its predecessor and nothing else below ever fires. Two
  consecutive identical pages cannot happen in a listing that is really being
  paged - the same items would have to be served twice - so the repeat is read
  as the listing having ended at the page before it, and its items are not
  handed back a second time.

The remaining three are checked after the page has been handed over, because the
items of such a page belong in the result:

* **The page is empty, or shorter than the first page.** The oldest signal and
  the one that ends almost every real listing. The length of the first page is
  the yardstick rather than the requested limit, because an instance may cap the
  page size below what was asked for.
* **The response says so.** `page_count` and `has_more` in a page's metadata are
  honoured when a caller reports them - Gitea sends the equivalent as headers on
  every page - and ignored when it does not, so this costs nothing to the
  callers that report neither.
* **The page limit.** A backstop for an instance that does none of the above:
  one cycling through pages, say, so that no two consecutive ones match.
  `MAX_PAGES` is far above any listing these endpoints return, so reaching it
  means something is wrong rather than that a listing is large, and it is logged
  rather than quietly truncating the result.

Only the empty-or-short rule is a judgement about the data; the rest are about
the instance being wrong, which is why they live here and not in each caller -
every paginated command is walked through these, so none of them can be the one
that still hangs.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable, Iterator

logger = logging.getLogger("gitea")

# Number of items requested per page when paging through a listing.
PAGE_SIZE = 50

# Most pages any one listing is walked over. At `PAGE_SIZE` a page, this is far
# more than the endpoints wrapped here return - the comments of one issue, the
# columns of one board, the issues of one column - so a walk reaching it has met
# an instance that will not say when to stop, not a listing that is simply long.
MAX_PAGES = 1000


def _is_last_page(batch: list[dict[str, Any]], page_size: int) -> bool:
    """Report whether a page is the last one of a listing by its size.

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


def _count(value: Any) -> int | None:
    """Read a count reported in a page's metadata.

    Args:
        value: The value the metadata carries.

    Returns:
        The count, or None when the value is not one. `True` is not one: it is
        an `int` as far as Python is concerned, and a metadata key set to a flag
        would otherwise be read as a listing one page long.

    """
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _reports_last_page(metadata: dict[str, Any], page: int) -> bool:
    """Report whether the response itself said this page was the last.

    Gitea reports the shape of a listing in the headers of every page, and a
    caller that carries them into the metadata gets termination from the
    server's own count rather than from the shape of the page it happened to
    send. Two keys are read, both optional:

    * `page_count` - the number of pages the listing has, as `X-PageCount`.
    * `has_more` - whether another page follows, as `X-HasMore`.

    Neither is required, and a metadata dictionary carrying neither leaves the
    walk to the other signals exactly as before.

    Args:
        metadata: The metadata of the page just fetched.
        page: The number of the page just fetched.

    Returns:
        True when the response reported that no page follows this one.

    """
    if not isinstance(metadata, dict):
        return False

    page_count = _count(metadata.get("page_count"))
    if page_count is not None and page >= page_count:
        return True

    return metadata.get("has_more") is False


def _repeats_previous(batch: list[dict[str, Any]], previous: list[dict[str, Any]] | None) -> bool:
    """Report whether a page is the page before it over again.

    An instance that ignores the `page` parameter answers every request with the
    same items, so no page is ever empty, short, or different from its
    predecessor and nothing else ends the walk.

    Two consecutive identical pages cannot happen in a listing that is really
    being paged: the same items would have to be served twice. So a repeat is
    read as the listing having ended at the page before, and the repeated items
    are not handed back - the caller already has them, and giving them again
    would put duplicates in a result that is meant to be a listing.

    Args:
        batch: The items of the page just fetched.
        previous: The items of the page before it, or None on the first page.

    Returns:
        True when the page is the previous one again.

    """
    return previous is not None and batch == previous


def _end_of_listing(
    *,
    batch: list[dict[str, Any]],
    metadata: dict[str, Any],
    page: int,
    page_size: int,
) -> str | None:
    """Decide whether a page ends the listing, and say why.

    Both walkers ask this rather than deciding for themselves, so the
    synchronous and the asynchronous walk cannot come to disagree about when a
    listing has ended.

    Args:
        batch: The items of the page just fetched.
        metadata: The metadata of the page just fetched.
        page: The number of the page just fetched.
        page_size: The size of the first page, or 0 while it is still unknown.

    Returns:
        Why the listing ends here, or None when another page is worth asking
        for. The reason is returned rather than a bare True because one of them
        - the page limit - means the result may be short, and a caller reading
        a log needs to know which one it was.

    """
    if _is_last_page(batch, page_size):
        return "the page was empty or shorter than the first"

    if _reports_last_page(metadata, page):
        return "the response reported it as the last page"

    if page >= MAX_PAGES:
        logger.warning(
            "Stopped walking a listing after %s pages without reaching its end; the result may be incomplete. "
            "The instance kept answering with a full page that differed from the one before it, so no page ever "
            "reported the listing as finished.",
            page,
        )
        return "the page limit was reached"

    return None


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
    previous: list[dict[str, Any]] | None = None
    while True:
        batch, metadata = fetch_page(page)

        if _repeats_previous(batch, previous):
            logger.debug(
                "Page %s of a listing repeated page %s; reading it as the end, since an instance that pages "
                "would not serve the same items twice.",
                page,
                page - 1,
            )
            return

        yield batch, metadata

        if _end_of_listing(batch=batch, metadata=metadata, page=page, page_size=page_size):
            return

        previous = batch
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
    previous: list[dict[str, Any]] | None = None
    while True:
        batch, metadata = await fetch_page(page)

        if _repeats_previous(batch, previous):
            logger.debug(
                "Page %s of a listing repeated page %s; reading it as the end, since an instance that pages "
                "would not serve the same items twice.",
                page,
                page - 1,
            )
            return

        yield batch, metadata

        if _end_of_listing(batch=batch, metadata=metadata, page=page, page_size=page_size):
            return

        previous = batch
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
