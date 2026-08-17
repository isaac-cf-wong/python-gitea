"""Unit tests for resolving the project column an issue's card sits in."""

import logging
from unittest.mock import MagicMock

import pytest
from requests import HTTPError

from gitea.issue.project_column import resolve_project_column_ids
from gitea.utils.pagination import PAGE_SIZE
from tests.board import (
    ISSUE_ID,
    ORGANIZATION_PROJECT,
    REPOSITORY_PROJECT,
    column_ids,
    make_client,
    make_issue,
    paged_issues,
)


def test_resolves_the_column_holding_the_card_of_an_organization_project():
    """The column listing the issue should become the project's column_id."""
    client = make_client(
        {29: [[{"id": 107, "title": "Backlog"}, {"id": 109, "title": "In Progress"}]]},
        {107: [[{"id": 1857}]], 109: [[{"id": ISSUE_ID}]]},
    )

    resolved = resolve_project_column_ids(
        client=client, owner="management", repository="weave-workspace", issue=make_issue(ORGANIZATION_PROJECT)
    )

    assert column_ids(resolved) == [109]
    # An organization project's columns live under the organization, not the repository.
    client.project.list_project_columns.assert_called_once_with(
        owner="management", repository=None, project_id=29, page=1, limit=PAGE_SIZE
    )
    assert {call.kwargs["repository"] for call in client.project.list_project_column_issues.call_args_list} == {None}


def test_resolves_the_column_of_a_repository_project_under_its_repository():
    """A repository project's columns should be listed under the repository holding it."""
    client = make_client(
        {31: [[{"id": 5, "title": "Doing"}]]},
        {5: [[{"id": ISSUE_ID}]]},
    )

    resolved = resolve_project_column_ids(
        client=client, owner="management", repository="weave-workspace", issue=make_issue(REPOSITORY_PROJECT)
    )

    assert column_ids(resolved) == [5]
    client.project.list_project_columns.assert_called_once_with(
        owner="management", repository="weave-workspace", project_id=31, page=1, limit=PAGE_SIZE
    )
    client.project.list_project_column_issues.assert_called_once_with(
        owner="management", repository="weave-workspace", project_id=31, column_id=5, page=1, limit=PAGE_SIZE
    )


def test_reports_no_column_when_the_issue_has_no_card_on_the_project():
    """A project whose columns do not list the issue should keep a null column."""
    client = make_client(
        {29: [[{"id": 107}, {"id": 108}]]},
        {107: [[{"id": 1857}]], 108: [[]]},
    )

    resolved = resolve_project_column_ids(
        client=client, owner="management", repository="weave-workspace", issue=make_issue(ORGANIZATION_PROJECT)
    )

    assert column_ids(resolved) == [None]
    # Every column of the project was searched before giving up. A page holding
    # items is followed by a request for the page after it, because a page filled
    # to the instance's cap cannot be told from the last one.
    assert [
        (call.kwargs["column_id"], call.kwargs["page"])
        for call in client.project.list_project_column_issues.call_args_list
    ] == [(107, 1), (107, 2), (108, 1)]


def test_resolves_every_project_the_issue_is_on():
    """Each project should get the column of its own card."""
    client = make_client(
        {29: [[{"id": 107}, {"id": 109}]], 31: [[{"id": 5}, {"id": 6}]]},
        {107: [[{"id": 1857}]], 109: [[{"id": ISSUE_ID}]], 5: [[]], 6: [[{"id": ISSUE_ID}]]},
    )

    resolved = resolve_project_column_ids(
        client=client,
        owner="management",
        repository="weave-workspace",
        issue=make_issue(ORGANIZATION_PROJECT, REPOSITORY_PROJECT),
    )

    assert column_ids(resolved) == [109, 6]


def test_stops_searching_at_the_column_holding_the_card():
    """The columns after the one holding the card should not be requested."""
    client = make_client(
        {29: [[{"id": 107}, {"id": 108}, {"id": 109}]]},
        {107: [[]], 108: [[{"id": ISSUE_ID}]], 109: [[{"id": ISSUE_ID}]]},
    )

    resolved = resolve_project_column_ids(
        client=client, owner="management", repository="weave-workspace", issue=make_issue(ORGANIZATION_PROJECT)
    )

    assert column_ids(resolved) == [108]
    assert [call.kwargs["column_id"] for call in client.project.list_project_column_issues.call_args_list] == [107, 108]


def test_finds_a_card_beyond_the_first_page_of_a_column():
    """A column's issues should be paged through until the card is found."""
    client = make_client(
        {29: [[{"id": 109}]]},
        {109: [[{"id": 1}, {"id": 2}], [{"id": 3}, {"id": ISSUE_ID}]]},
    )

    resolved = resolve_project_column_ids(
        client=client, owner="management", repository="weave-workspace", issue=make_issue(ORGANIZATION_PROJECT)
    )

    assert column_ids(resolved) == [109]
    assert [call.kwargs["page"] for call in client.project.list_project_column_issues.call_args_list] == [1, 2]


def test_finds_a_card_in_a_column_beyond_the_first_page_of_columns():
    """A project's columns should be paged through until the card is found."""
    client = make_client(
        {29: [[{"id": 101}, {"id": 102}], [{"id": 103}, {"id": 109}]]},
        {101: [[]], 102: [[]], 103: [[]], 109: [[{"id": ISSUE_ID}]]},
    )

    resolved = resolve_project_column_ids(
        client=client, owner="management", repository="weave-workspace", issue=make_issue(ORGANIZATION_PROJECT)
    )

    assert column_ids(resolved) == [109]
    assert [call.kwargs["page"] for call in client.project.list_project_columns.call_args_list] == [1, 2]


def test_returns_the_issue_unchanged_when_it_lists_no_projects():
    """An issue payload without a projects field should cost no requests."""
    client = make_client({}, {})
    issue = {"id": ISSUE_ID, "title": "No board"}

    resolved = resolve_project_column_ids(client=client, owner="management", repository="weave-workspace", issue=issue)

    assert resolved == issue
    client.project.list_project_columns.assert_not_called()


def test_returns_the_issue_unchanged_when_the_projects_field_is_null():
    """The API reporting no projects as null should be treated as no projects."""
    client = make_client({}, {})
    issue = {"id": ISSUE_ID, "title": "No board", "projects": None}

    resolved = resolve_project_column_ids(client=client, owner="management", repository="weave-workspace", issue=issue)

    assert resolved == issue
    client.project.list_project_columns.assert_not_called()


def test_returns_a_payload_that_is_not_an_issue_object_unchanged():
    """A body that is not an issue must be handed back rather than crashed on."""
    client = make_client({}, {})

    assert resolve_project_column_ids(client=client, owner="management", repository="weave-workspace", issue=[]) == []
    client.project.list_project_columns.assert_not_called()


def test_returns_the_issue_unchanged_without_a_global_issue_id():
    """Column listings identify issues by global ID, so without one nothing can be matched."""
    client = make_client({}, {})
    issue = {"number": 15, "projects": [dict(ORGANIZATION_PROJECT)]}

    resolved = resolve_project_column_ids(client=client, owner="management", repository="weave-workspace", issue=issue)

    assert resolved == issue
    client.project.list_project_columns.assert_not_called()


def test_reports_no_column_for_a_project_without_a_usable_id():
    """A project the columns cannot be listed for should keep a null column."""
    client = make_client({}, {})

    resolved = resolve_project_column_ids(
        client=client,
        owner="management",
        repository="weave-workspace",
        issue=make_issue({"title": "Nameless board"}),
    )

    assert column_ids(resolved) == [None]
    client.project.list_project_columns.assert_not_called()


def test_skips_a_column_without_a_usable_id():
    """A column the issues cannot be listed for should not be searched."""
    client = make_client(
        {29: [[{"title": "Nameless"}, {"id": 109}]]},
        {109: [[{"id": ISSUE_ID}]]},
    )

    resolved = resolve_project_column_ids(
        client=client, owner="management", repository="weave-workspace", issue=make_issue(ORGANIZATION_PROJECT)
    )

    assert column_ids(resolved) == [109]
    assert [call.kwargs["column_id"] for call in client.project.list_project_column_issues.call_args_list] == [109]


def test_a_refused_lookup_leaves_that_project_null_and_resolves_the_others(caplog):
    """A failed lookup should cost only its own column, not the issue or the other projects."""
    client = MagicMock()
    client.project.list_project_columns.side_effect = [
        HTTPError("404 Client Error"),
        ([{"id": 6}], {"status_code": 200}),
    ]
    client.project.list_project_column_issues.side_effect = paged_issues({6: [[{"id": ISSUE_ID}]]})

    with caplog.at_level(logging.WARNING, logger="gitea"):
        resolved = resolve_project_column_ids(
            client=client,
            owner="management",
            repository="weave-workspace",
            issue=make_issue(ORGANIZATION_PROJECT, REPOSITORY_PROJECT),
        )

    assert column_ids(resolved) == [None, 6]
    assert "29" in caplog.text
    assert "404 Client Error" in caplog.text


def test_keeps_the_rest_of_the_issue_and_of_the_projects_intact():
    """Only column_id should be added; nothing else may be dropped or rewritten."""
    client = make_client({29: [[{"id": 109}]]}, {109: [[{"id": ISSUE_ID}]]})
    issue = make_issue(ORGANIZATION_PROJECT)

    resolved = resolve_project_column_ids(client=client, owner="management", repository="weave-workspace", issue=issue)

    assert resolved == {**issue, "projects": [{**ORGANIZATION_PROJECT, "column_id": 109}]}
    # The payload handed in is not mutated.
    assert issue["projects"] == [ORGANIZATION_PROJECT]


@pytest.mark.parametrize(
    ("project", "expected_repository"),
    [
        ({"id": 29, "type": "organization", "repo_id": 0}, None),
        ({"id": 31, "type": "repository", "repo_id": 4}, "weave-workspace"),
        # An older instance may report the type without the repository, or the
        # repository without the type; either alone identifies the scope.
        ({"id": 31, "repo_id": 4}, "weave-workspace"),
        ({"id": 29, "type": "organization"}, None),
        ({"id": 29}, None),
    ],
)
def test_scopes_the_column_listing_to_the_kind_of_project(project, expected_repository):
    """The column listing should be scoped by the kind of project the card is on."""
    client = make_client({project["id"]: [[{"id": 7}]]}, {7: [[{"id": ISSUE_ID}]]})

    resolve_project_column_ids(
        client=client, owner="management", repository="weave-workspace", issue=make_issue(project)
    )

    assert client.project.list_project_columns.call_args.kwargs["repository"] == expected_repository
