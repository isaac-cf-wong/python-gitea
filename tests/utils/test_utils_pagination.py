"""Unit tests for the paginated-listing helpers."""

import inspect
from unittest.mock import patch

import pytest

from gitea.utils import pagination
from gitea.utils.pagination import (
    MAX_PAGES,
    PAGE_LIMIT,
    REPEATED_PAGE,
    REPORTED_LAST_PAGE,
    SHORT_PAGE,
    _end_of_listing,
    collect_all_pages,
    iter_async_pages,
    iter_pages,
)


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


def make_repeating_fetch_page(batch, requested=None, limit=50):
    """Build a page fetcher that answers every page number with the same items.

    This is how an instance that ignores the `page` parameter behaves: the
    listing never runs out, so a walker relying on an empty or short page to
    end it asks for page 3, page 4 and page 5 forever.

    Args:
        batch: The items every page comes back with.
        requested: List recording the page numbers requested, if given.
        limit: Requests after which to give up, so a walker that does not
            terminate fails the test instead of hanging the suite.

    Returns:
        A callable answering every page with the same items.

    """
    served = []

    def fetch_page(page):
        served.append(page)
        if requested is not None:
            requested.append(page)
        if len(served) > limit:
            raise AssertionError(f"the listing was still being walked after {len(served)} requests")
        return (list(batch), {"status_code": 200, "page": page})

    return fetch_page


class TestRepeatedPage:
    """Tests for an instance that answers every page number with the same items."""

    def test_a_repeated_page_ends_the_listing(self):
        """The walk has to stop, which is the whole bug: it used to run forever."""
        requested: list[int] = []

        items, _ = collect_all_pages(make_repeating_fetch_page([{"id": 101}, {"id": 102}], requested))

        assert requested == [1, 2]
        assert [item["id"] for item in items] == [101, 102]

    def test_the_repeated_items_are_not_returned_twice(self):
        """The page that ends the listing is the caller's page 1 over again.

        Handing it back would put every item in the result twice, which for a
        listing of columns or issues is a duplicate row rather than a duplicate
        the caller can collapse.
        """
        items, _ = collect_all_pages(make_repeating_fetch_page([{"id": 1}, {"id": 2}, {"id": 3}]))

        assert [item["id"] for item in items] == [1, 2, 3]

    def test_a_listing_repeating_after_several_real_pages_keeps_those_pages(self):
        """Only the repeat is dropped, not the pages walked before it."""
        pages = [[{"id": 1}, {"id": 2}], [{"id": 3}, {"id": 4}], [{"id": 3}, {"id": 4}]]
        requested: list[int] = []

        items, _ = collect_all_pages(make_fetch_page(pages, requested))

        assert [item["id"] for item in items] == [1, 2, 3, 4]
        assert requested == [1, 2, 3]

    def test_two_pages_of_equal_length_but_different_items_are_both_walked(self):
        """Repetition is about the items, not about the shape of the page."""
        pages = [[{"id": 1}, {"id": 2}], [{"id": 3}, {"id": 4}], []]
        requested: list[int] = []

        items, _ = collect_all_pages(make_fetch_page(pages, requested))

        assert [item["id"] for item in items] == [1, 2, 3, 4]
        assert requested == [1, 2, 3]


class TestReportedPagination:
    """Tests for a caller that carries the response's own pagination into metadata."""

    def test_a_reported_page_count_ends_the_listing(self):
        """`page_count` says how many pages there are, so the last one is known."""
        requested: list[int] = []

        def fetch_page(page):
            requested.append(page)
            if len(requested) > 20:
                raise AssertionError(f"the reported pagination did not end the walk after {len(requested)} requests")
            return ([{"id": page}] * 2, {"status_code": 200, "page_count": 2})

        items, _ = collect_all_pages(fetch_page)

        assert requested == [1, 2]
        assert len(items) == 4

    def test_has_more_being_false_ends_the_listing(self):
        """`has_more` answers the question directly when the instance sends it."""
        requested: list[int] = []

        def fetch_page(page):
            requested.append(page)
            if len(requested) > 20:
                raise AssertionError(f"the reported pagination did not end the walk after {len(requested)} requests")
            return ([{"id": page}] * 2, {"status_code": 200, "has_more": page < 2})

        items, _ = collect_all_pages(fetch_page)

        assert requested == [1, 2]
        assert len(items) == 4

    @pytest.mark.parametrize(
        "metadata",
        [
            {"status_code": 200},
            {"status_code": 200, "page_count": None},
            {"status_code": 200, "page_count": "2"},
            {"status_code": 200, "page_count": True},
            {"status_code": 200, "has_more": True},
            # Reported, but saying nothing: read as "no answer" rather than as
            # "no more", so a caller carrying the key through without a value
            # does not truncate the listing at its first page.
            {"status_code": 200, "has_more": None},
            {"status_code": 200, "has_more": ""},
        ],
    )
    def test_metadata_reporting_nothing_usable_leaves_the_other_signals_to_decide(self, metadata):
        """A caller reporting nothing must keep the behaviour it had.

        Args:
            metadata: The metadata each page comes back with.

        """
        pages = [[{"id": 1}, {"id": 2}], [{"id": 3}]]
        requested: list[int] = []

        def fetch_page(page):
            requested.append(page)
            return (list(pages[page - 1]) if page <= len(pages) else [], metadata)

        items, _ = collect_all_pages(fetch_page)

        # Ended by the short second page, as it did before any of this.
        assert [item["id"] for item in items] == [1, 2, 3]
        assert requested == [1, 2]


class TestPageLimit:
    """Tests for the backstop against an instance that never says when to stop."""

    def test_a_listing_that_never_ends_stops_at_the_page_limit(self):
        """A page differing from the one before it every time still terminates."""
        requested: list[int] = []

        def fetch_page(page):
            requested.append(page)
            # Bounded above the limit, so a walk that stopped honouring it fails
            # this test rather than hanging the suite that runs it.
            if len(requested) > MAX_PAGES + 10:
                raise AssertionError(f"the page limit did not end the walk after {len(requested)} requests")
            # Never empty, never short, never a repeat: nothing else can end it.
            return ([{"id": page * 10 + n} for n in range(2)], {"status_code": 200})

        with patch("gitea.utils.pagination.logger") as logger:
            items, _ = collect_all_pages(fetch_page)

        assert len(requested) == MAX_PAGES
        assert len(items) == MAX_PAGES * 2
        # Truncating a result silently would leave the caller believing it had
        # the whole listing.
        assert logger.warning.call_count == 1

    def test_an_ordinary_listing_never_reaches_the_limit(self):
        """The backstop must not be what ends a listing that ends by itself."""
        requested: list[int] = []

        collect_all_pages(make_fetch_page([[{"id": 1}, {"id": 2}], [{"id": 3}]], requested))

        assert requested == [1, 2]


@pytest.mark.asyncio
async def test_iter_async_pages_stops_on_a_repeated_page():
    """The asynchronous walk has to end on a repeat as the synchronous one does."""
    requested: list[int] = []
    fetch_page = make_repeating_fetch_page([{"id": 101}, {"id": 102}], requested)

    async def fetch_page_async(page):
        return fetch_page(page)

    seen = [batch async for batch, _ in iter_async_pages(fetch_page_async)]

    assert requested == [1, 2]
    assert [item["id"] for batch in seen for item in batch] == [101, 102]


@pytest.mark.asyncio
async def test_iter_async_pages_stops_at_the_page_limit():
    """The backstop has to hold on the asynchronous walk too."""
    requested: list[int] = []

    async def fetch_page_async(page):
        requested.append(page)
        if len(requested) > MAX_PAGES + 10:
            raise AssertionError(f"the page limit did not end the walk after {len(requested)} requests")
        return ([{"id": page * 10 + n} for n in range(2)], {"status_code": 200})

    with patch("gitea.utils.pagination.logger") as logger:
        seen = [batch async for batch, _ in iter_async_pages(fetch_page_async)]

    assert len(requested) == MAX_PAGES
    assert len(seen) == MAX_PAGES
    assert logger.warning.call_count == 1


@pytest.mark.asyncio
async def test_iter_async_pages_honours_a_reported_page_count():
    """The reported pagination has to be read on the asynchronous walk too."""
    requested: list[int] = []

    async def fetch_page_async(page):
        requested.append(page)
        if len(requested) > 20:
            raise AssertionError(f"the reported pagination did not end the walk after {len(requested)} requests")
        return ([{"id": page}] * 2, {"status_code": 200, "page_count": 3})

    seen = [batch async for batch, _ in iter_async_pages(fetch_page_async)]

    assert requested == [1, 2, 3]
    assert len(seen) == 3


class TestEndOfListing:
    """Tests for the one place every rule that ends a walk is written down."""

    def test_a_repeat_is_the_first_rule_asked(self):
        """The repeat has to win over every other ending, and drop its page.

        The page below satisfies all four rules at once, which no real walk
        reaches - but it is the only way to assert which one is consulted first
        rather than inferring it from a walk that happens to agree.
        """
        verdict = _end_of_listing(
            batch=[{"id": 1}],
            metadata={"page_count": 1, "has_more": False},
            previous=[{"id": 1}],
            page=MAX_PAGES,
            page_size=99,
        )

        assert verdict.reason == REPEATED_PAGE
        # The items are the caller's page 1 over again, so they are not handed
        # back; every other ending hands its page over.
        assert verdict.include is False

    @pytest.mark.parametrize(
        ("batch", "metadata", "page", "page_size", "reason"),
        [
            ([], {}, 1, 0, SHORT_PAGE),
            ([{"id": 1}], {}, 2, 2, SHORT_PAGE),
            ([{"id": 1}], {"page_count": 1}, 1, 1, REPORTED_LAST_PAGE),
            ([{"id": 1}], {"has_more": False}, 1, 1, REPORTED_LAST_PAGE),
            ([{"id": 1}], {}, MAX_PAGES, 1, PAGE_LIMIT),
        ],
    )
    def test_every_other_ending_hands_its_page_over(self, batch, metadata, page, page_size, reason):
        """The page that ends a listing belongs to it, unless it is a repeat.

        Args:
            batch: The items of the page just fetched.
            metadata: The metadata of the page just fetched.
            page: The number of the page just fetched.
            page_size: The size of the first page.
            reason: The ending expected.

        """
        verdict = _end_of_listing(
            batch=batch,
            metadata=metadata,
            previous=[{"id": 2}],
            page=page,
            page_size=page_size,
        )

        assert verdict.reason == reason
        assert verdict.include is True

    def test_a_page_with_nothing_to_end_it_keeps_the_walk_going(self):
        """The ordinary case: hand the page over and ask for the next one."""
        verdict = _end_of_listing(
            batch=[{"id": 1}, {"id": 2}],
            metadata={"status_code": 200},
            previous=[{"id": 3}, {"id": 4}],
            page=2,
            page_size=2,
        )

        assert verdict.reason is None
        assert verdict.include is True

    def test_the_walkers_decide_nothing_of_their_own(self):
        """Neither walker may re-implement a rule instead of asking for it.

        The rules were written out in both walkers once, which is how they came
        to disagree about handing a repeated page over. Asserting the source
        keeps them delegating rather than only that they currently agree.
        """
        source = inspect.getsource(pagination)
        walkers = source[source.index("def iter_pages(") : source.index("def collect_all_pages(")]

        assert walkers.count("_end_of_listing(") == 2
        for rule in ("_repeats_previous", "_is_last_page", "_reports_last_page", "MAX_PAGES"):
            assert rule not in walkers, f"{rule} is applied in a walker rather than in _end_of_listing"


class TestReportedPageCountIsPositive:
    """Tests for a page count that does not describe a listing."""

    @pytest.mark.parametrize("page_count", [0, -1, -100])
    def test_a_page_count_of_zero_or_less_does_not_end_a_full_first_page(self, page_count):
        """Taking such a count at its word would throw away a listing that has items.

        Args:
            page_count: The count the metadata reports.

        """
        pages = [[{"id": 1}, {"id": 2}], [{"id": 3}]]
        requested: list[int] = []

        def fetch_page(page):
            requested.append(page)
            if len(requested) > 20:
                raise AssertionError(f"the walk did not end after {len(requested)} requests")
            return (list(pages[page - 1]) if page <= len(pages) else [], {"page_count": page_count})

        items, _ = collect_all_pages(fetch_page)

        assert [item["id"] for item in items] == [1, 2, 3]
        assert requested == [1, 2]

    def test_a_page_count_of_one_still_ends_the_first_page(self):
        """The smallest count that describes a listing has to be honoured."""
        requested: list[int] = []

        def fetch_page(page):
            requested.append(page)
            if len(requested) > 20:
                raise AssertionError(f"the walk did not end after {len(requested)} requests")
            return ([{"id": page}] * 2, {"page_count": 1})

        items, _ = collect_all_pages(fetch_page)

        assert requested == [1]
        assert len(items) == 2


@pytest.mark.asyncio
async def test_iter_async_pages_drops_a_repeat_that_other_rules_would_have_kept():
    """The asynchronous walk has to read the same verdict as the synchronous one.

    The repeated page also reports itself as the last, so a walk consulting the
    reported pagination first would hand its items over and duplicate them.
    """
    requested: list[int] = []

    async def fetch_page_async(page):
        requested.append(page)
        if len(requested) > 20:
            raise AssertionError(f"the walk did not end after {len(requested)} requests")
        return ([{"id": 1}, {"id": 2}], {"page_count": 2})

    seen = [batch async for batch, _ in iter_async_pages(fetch_page_async)]

    assert requested == [1, 2]
    assert [item["id"] for batch in seen for item in batch] == [1, 2]


def test_iter_pages_drops_a_repeat_that_other_rules_would_have_kept():
    """The synchronous twin of the walk above, for the same reason."""
    requested: list[int] = []

    def fetch_page(page):
        requested.append(page)
        if len(requested) > 20:
            raise AssertionError(f"the walk did not end after {len(requested)} requests")
        return ([{"id": 1}, {"id": 2}], {"page_count": 2})

    items, _ = collect_all_pages(fetch_page)

    assert requested == [1, 2]
    assert [item["id"] for item in items] == [1, 2]
