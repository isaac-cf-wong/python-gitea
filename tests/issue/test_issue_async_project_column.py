"""Unit tests for resolving project columns with the asynchronous client."""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import ClientError

from gitea.issue.project_column import resolve_async_project_column_ids
from gitea.utils.pagination import PAGE_SIZE
from tests.board import (
    ISSUE_ID,
    ORGANIZATION_PROJECT,
    REPOSITORY_PROJECT,
    column_ids,
    make_async_client,
    make_issue,
    make_issue_with_projects,
    paged_issues,
)


@pytest.mark.asyncio
async def test_resolves_the_column_holding_the_card():
    """The column listing the issue should become the project's column_id."""
    client = make_async_client(
        {29: [[{"id": 107}, {"id": 109}]]},
        {107: [[{"id": 1857}]], 109: [[{"id": ISSUE_ID}]]},
    )

    resolved = await resolve_async_project_column_ids(
        client=client, owner="example-org", repository="example-repo", issue=make_issue(ORGANIZATION_PROJECT)
    )

    assert column_ids(resolved) == [109]
    client.project.list_project_columns.assert_awaited_once_with(
        owner="example-org", repository=None, project_id=29, page=1, limit=PAGE_SIZE
    )


@pytest.mark.asyncio
async def test_resolves_the_column_of_a_repository_project_under_its_repository():
    """A repository project's columns should be listed under the repository holding it."""
    client = make_async_client({31: [[{"id": 5}]]}, {5: [[{"id": ISSUE_ID}]]})

    resolved = await resolve_async_project_column_ids(
        client=client, owner="example-org", repository="example-repo", issue=make_issue(REPOSITORY_PROJECT)
    )

    assert column_ids(resolved) == [5]
    client.project.list_project_columns.assert_awaited_once_with(
        owner="example-org", repository="example-repo", project_id=31, page=1, limit=PAGE_SIZE
    )


@pytest.mark.asyncio
async def test_reports_no_column_when_the_issue_has_no_card_on_the_project():
    """A project whose columns do not list the issue should keep a null column."""
    client = make_async_client({29: [[{"id": 107}, {"id": 108}]]}, {107: [[{"id": 1857}]], 108: [[]]})

    resolved = await resolve_async_project_column_ids(
        client=client, owner="example-org", repository="example-repo", issue=make_issue(ORGANIZATION_PROJECT)
    )

    assert column_ids(resolved) == [None]
    # Both columns were searched; a page holding items is followed by a request
    # for the page after it, because a full page cannot be told from a last one.
    assert [
        (call.kwargs["column_id"], call.kwargs["page"])
        for call in client.project.list_project_column_issues.await_args_list
    ] == [(107, 1), (107, 2), (108, 1)]


@pytest.mark.asyncio
async def test_pages_through_columns_and_their_issues():
    """Both listings should be paged through until the card is found."""
    client = make_async_client(
        {29: [[{"id": 101}, {"id": 102}], [{"id": 109}]]},
        {101: [[]], 102: [[{"id": 1}, {"id": 2}], [{"id": ISSUE_ID}]]},
    )

    resolved = await resolve_async_project_column_ids(
        client=client, owner="example-org", repository="example-repo", issue=make_issue(ORGANIZATION_PROJECT)
    )

    assert column_ids(resolved) == [102]
    assert [
        (call.kwargs["column_id"], call.kwargs["page"])
        for call in client.project.list_project_column_issues.await_args_list
    ] == [(101, 1), (102, 1), (102, 2)]


@pytest.mark.asyncio
async def test_reports_no_column_for_a_project_without_a_usable_id():
    """A project the columns cannot be listed for should keep a null column."""
    client = make_async_client({}, {})

    resolved = await resolve_async_project_column_ids(
        client=client,
        owner="example-org",
        repository="example-repo",
        issue=make_issue({"title": "Nameless board"}),
    )

    assert column_ids(resolved) == [None]
    client.project.list_project_columns.assert_not_awaited()


@pytest.mark.asyncio
async def test_returns_the_issue_unchanged_when_it_lists_no_projects():
    """An issue payload without a projects field should cost no requests."""
    client = make_async_client({}, {})
    issue = {"id": ISSUE_ID, "title": "No board"}

    resolved = await resolve_async_project_column_ids(
        client=client, owner="example-org", repository="example-repo", issue=issue
    )

    assert resolved == issue
    client.project.list_project_columns.assert_not_awaited()


@pytest.mark.asyncio
async def test_a_refused_lookup_leaves_that_project_null_and_resolves_the_others(caplog):
    """A failed lookup should cost only its own column, not the issue or the other projects."""
    client = MagicMock()
    client.project.list_project_columns = AsyncMock(
        side_effect=[
            ClientError("404 Not Found"),
            ([{"id": 6}], {"status_code": 200}),
        ]
    )
    client.project.list_project_column_issues = AsyncMock(side_effect=paged_issues({6: [[{"id": ISSUE_ID}]]}))

    with caplog.at_level(logging.WARNING, logger="gitea"):
        resolved = await resolve_async_project_column_ids(
            client=client,
            owner="example-org",
            repository="example-repo",
            issue=make_issue(ORGANIZATION_PROJECT, REPOSITORY_PROJECT),
        )

    assert column_ids(resolved) == [None, 6]
    assert "29" in caplog.text
    assert "404 Not Found" in caplog.text


@pytest.mark.asyncio
async def test_a_timed_out_lookup_leaves_that_project_null_and_resolves_the_others(caplog):
    """Aiohttp raises its total timeout as a bare TimeoutError, not a ClientError.

    A transient timeout must degrade to a null column like any other failed
    lookup, as it does on the synchronous path where requests reports a timeout
    as a RequestException.
    """
    client = MagicMock()
    client.project.list_project_columns = AsyncMock(
        side_effect=[
            TimeoutError("Timeout on reading data from socket"),
            ([{"id": 6}], {"status_code": 200}),
        ]
    )
    client.project.list_project_column_issues = AsyncMock(side_effect=paged_issues({6: [[{"id": ISSUE_ID}]]}))

    with caplog.at_level(logging.WARNING, logger="gitea"):
        resolved = await resolve_async_project_column_ids(
            client=client,
            owner="example-org",
            repository="example-repo",
            issue=make_issue(ORGANIZATION_PROJECT, REPOSITORY_PROJECT),
        )

    assert column_ids(resolved) == [None, 6]
    assert "29" in caplog.text
    assert "Timeout on reading data from socket" in caplog.text


@pytest.mark.asyncio
async def test_a_timeout_raised_as_asyncio_timeout_error_is_caught():
    """asyncio.TimeoutError is the alias the client's own timeouts surface under."""
    client = MagicMock()
    client.project.list_project_columns = AsyncMock(side_effect=asyncio.TimeoutError)

    resolved = await resolve_async_project_column_ids(
        client=client, owner="example-org", repository="example-repo", issue=make_issue(ORGANIZATION_PROJECT)
    )

    assert column_ids(resolved) == [None]


@pytest.mark.asyncio
async def test_reports_a_null_column_without_a_global_issue_id():
    """Without a global ID nothing can be matched, but the field is attached all the same."""
    client = make_async_client({}, {})
    issue = {"number": 15, "projects": [dict(ORGANIZATION_PROJECT)]}

    resolved = await resolve_async_project_column_ids(
        client=client, owner="example-org", repository="example-repo", issue=issue
    )

    assert resolved == {**issue, "projects": [{**ORGANIZATION_PROJECT, "column_id": None}]}
    client.project.list_project_columns.assert_not_awaited()


@pytest.mark.asyncio
async def test_passes_a_project_entry_that_is_not_an_object_through_untouched():
    """A malformed entry has nothing to attach a column to, so it must not crash the lookup."""
    client = make_async_client({29: [[{"id": 109}]]}, {109: [[{"id": ISSUE_ID}]]})

    resolved = await resolve_async_project_column_ids(
        client=client,
        owner="example-org",
        repository="example-repo",
        issue=make_issue_with_projects(["not a project", None, dict(ORGANIZATION_PROJECT)]),
    )

    assert resolved["projects"] == ["not a project", None, {**ORGANIZATION_PROJECT, "column_id": 109}]


@pytest.mark.asyncio
async def test_skips_a_column_entry_that_is_not_an_object():
    """A malformed column carries no ID to list issues by, so it must be skipped rather than crash."""
    client = make_async_client({29: [[None, "not a column", {"id": 109}]]}, {109: [[{"id": ISSUE_ID}]]})

    resolved = await resolve_async_project_column_ids(
        client=client, owner="example-org", repository="example-repo", issue=make_issue(ORGANIZATION_PROJECT)
    )

    assert column_ids(resolved) == [109]
    assert [call.kwargs["column_id"] for call in client.project.list_project_column_issues.await_args_list] == [109]
