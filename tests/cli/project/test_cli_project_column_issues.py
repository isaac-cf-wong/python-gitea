"""Unit tests for the project column-issue listing CLI commands."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from gitea.cli.main import app
from gitea.cli.project.column.issues import list_column_issues_command
from gitea.cli.project.issues import PAGE_SIZE, _collect_all_pages, list_project_issues_command

runner = CliRunner()

ISSUES = [
    {"number": 7, "title": "Fix the docs", "state": "open"},
    {"number": 9, "title": "Ship the release", "state": "closed"},
]


def make_ctx():
    """Create a mock context object."""
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


def paged_columns(*pages):
    """Build a side effect serving one page of columns per requested page number.

    Args:
        *pages: The columns of each page, in order.

    Returns:
        A side effect returning the requested page, or an empty page beyond the last one.

    """

    def _side_effect(**kwargs):
        page = kwargs.get("page", 1)
        return (list(pages[page - 1]) if page <= len(pages) else [], {"status_code": 200})

    return _side_effect


def paged_issues(pages_by_column):
    """Build a side effect serving one page of issues per column and requested page number.

    Args:
        pages_by_column: Mapping of column ID to that column's pages of issues.

    Returns:
        A side effect returning the requested page, or an empty page beyond the last one.

    """

    def _side_effect(**kwargs):
        pages = pages_by_column[kwargs["column_id"]]
        page = kwargs.get("page", 1)
        return (list(pages[page - 1]) if page <= len(pages) else [], {"status_code": 200})

    return _side_effect


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_list_column_issues_command(mock_gitea, mock_get_auth_params, mock_execute):
    """list_column_issues_command should wire auth and call list_project_column_issues."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.list_project_column_issues.return_value = (ISSUES, {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    list_column_issues_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        column_id=5,
        page=2,
        limit=10,
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli project column issues"

    result = call_kwargs["api_call"]()
    client.project.list_project_column_issues.assert_called_once_with(
        owner="owner", repository="repo", project_id=1, column_id=5, page=2, limit=10
    )
    assert result == (ISSUES, {"status_code": 200})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_list_column_issues_command_organization_project(mock_gitea, mock_get_auth_params, mock_execute):
    """Omitting the repository should list issues on an organization project's column."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.list_project_column_issues.return_value = (ISSUES, {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    list_column_issues_command(
        ctx=ctx,
        owner="my-org",
        project_id=1,
        column_id=5,
    )

    call_kwargs = mock_execute.call_args[1]
    call_kwargs["api_call"]()
    client.project.list_project_column_issues.assert_called_once_with(
        owner="my-org", repository=None, project_id=1, column_id=5, page=None, limit=None
    )


@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_list_column_issues_output_envelope(mock_gitea, mock_get_auth_params):
    """`project column issues` should print the issues in the standard JSON envelope."""
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.list_project_column_issues.return_value = (ISSUES, {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    result = runner.invoke(
        app,
        ["project", "column", "issues", "--owner", "my-org", "--project-id", "1", "--column-id", "5"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload == {"data": ISSUES, "metadata": {"status_code": 200}}
    assert [issue["number"] for issue in payload["data"]] == [7, 9]


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_list_project_issues_command(mock_gitea, mock_get_auth_params, mock_execute):
    """list_project_issues_command should group each column's issues under that column."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.list_project_columns.side_effect = paged_columns(
        [{"id": 5, "title": "Todo"}, {"id": 6, "title": "Done"}]
    )
    client.project.list_project_column_issues.side_effect = paged_issues({5: [ISSUES[:1]], 6: [ISSUES[1:]]})
    mock_gitea.return_value.__enter__.return_value = client

    list_project_issues_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli project issues"

    data, metadata = call_kwargs["api_call"]()
    assert client.project.list_project_columns.call_args_list[0].kwargs == {
        "owner": "owner",
        "repository": "repo",
        "project_id": 1,
        "page": 1,
        "limit": PAGE_SIZE,
    }
    assert client.project.list_project_column_issues.call_args_list[0].kwargs == {
        "owner": "owner",
        "repository": "repo",
        "project_id": 1,
        "column_id": 5,
        "page": 1,
        "limit": PAGE_SIZE,
    }
    assert [call.kwargs["column_id"] for call in client.project.list_project_column_issues.call_args_list] == [
        5,
        5,
        6,
        6,
    ]
    assert data == [
        {"column": {"id": 5, "title": "Todo"}, "issues": ISSUES[:1]},
        {"column": {"id": 6, "title": "Done"}, "issues": ISSUES[1:]},
    ]
    assert metadata == {"status_code": 200, "column_count": 2, "issue_count": 2}


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_list_project_issues_command_organization_project(mock_gitea, mock_get_auth_params, mock_execute):
    """Omitting the repository should list an organization project's issues."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.list_project_columns.side_effect = paged_columns([{"id": 5, "title": "Todo"}])
    client.project.list_project_column_issues.side_effect = paged_issues({5: [ISSUES]})
    mock_gitea.return_value.__enter__.return_value = client

    list_project_issues_command(ctx=ctx, owner="my-org", project_id=1)

    call_kwargs = mock_execute.call_args[1]
    call_kwargs["api_call"]()
    assert client.project.list_project_columns.call_args_list[0].kwargs == {
        "owner": "my-org",
        "repository": None,
        "project_id": 1,
        "page": 1,
        "limit": PAGE_SIZE,
    }
    assert client.project.list_project_column_issues.call_args_list[0].kwargs == {
        "owner": "my-org",
        "repository": None,
        "project_id": 1,
        "column_id": 5,
        "page": 1,
        "limit": PAGE_SIZE,
    }


@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_list_project_issues_output_envelope(mock_gitea, mock_get_auth_params):
    """`project issues` should print the grouped cards in the standard JSON envelope."""
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.list_project_columns.side_effect = paged_columns([{"id": 5, "title": "Todo"}])
    client.project.list_project_column_issues.side_effect = paged_issues({5: [ISSUES]})
    mock_gitea.return_value.__enter__.return_value = client

    result = runner.invoke(app, ["project", "issues", "--owner", "my-org", "--project-id", "1"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload == {
        "data": [{"column": {"id": 5, "title": "Todo"}, "issues": ISSUES}],
        "metadata": {"status_code": 200, "column_count": 1, "issue_count": 2},
    }


@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_list_project_issues_spans_every_page(mock_gitea, mock_get_auth_params):
    """`project issues` should aggregate every page of columns and of each column's issues."""
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    columns_page_1 = [{"id": 5, "title": "Todo"}, {"id": 6, "title": "Doing"}]
    columns_page_2 = [{"id": 7, "title": "Done"}]
    todo_issues = [{"number": n, "title": f"Issue {n}", "state": "open"} for n in (1, 2, 3)]
    doing_issues = [{"number": 4, "title": "Issue 4", "state": "open"}]

    client = MagicMock()
    client.project.list_project_columns.side_effect = paged_columns(columns_page_1, columns_page_2)
    client.project.list_project_column_issues.side_effect = paged_issues(
        {
            5: [todo_issues[:2], todo_issues[2:]],
            6: [doing_issues],
            7: [],
        }
    )
    mock_gitea.return_value.__enter__.return_value = client

    result = runner.invoke(app, ["project", "issues", "--owner", "my-org", "--project-id", "1"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"] == [
        {"column": {"id": 5, "title": "Todo"}, "issues": todo_issues},
        {"column": {"id": 6, "title": "Doing"}, "issues": doing_issues},
        {"column": {"id": 7, "title": "Done"}, "issues": []},
    ]
    assert payload["metadata"] == {"status_code": 200, "column_count": 3, "issue_count": 4}
    assert [call.kwargs["page"] for call in client.project.list_project_columns.call_args_list] == [1, 2]
    assert [
        (call.kwargs["column_id"], call.kwargs["page"])
        for call in client.project.list_project_column_issues.call_args_list
    ] == [(5, 1), (5, 2), (6, 1), (6, 2), (7, 1)]


@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_list_project_issues_spans_several_continuation_pages(mock_gitea, mock_get_auth_params):
    """Full pages should keep being followed until a short one ends the listing."""
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    columns = [{"id": column_id, "title": f"Column {column_id}"} for column_id in (5, 6, 7, 8, 9)]
    todo_issues = [{"number": n, "title": f"Issue {n}", "state": "open"} for n in (1, 2, 3, 4, 5)]

    client = MagicMock()
    # Three pages of columns, of lengths 2, 2 and 1: two continuations, then a short page.
    client.project.list_project_columns.side_effect = paged_columns(columns[:2], columns[2:4], columns[4:])
    # Column 5 likewise holds three pages of issues, of lengths 2, 2 and 1.
    client.project.list_project_column_issues.side_effect = paged_issues(
        {
            5: [todo_issues[:2], todo_issues[2:4], todo_issues[4:]],
            6: [],
            7: [],
            8: [],
            9: [],
        }
    )
    mock_gitea.return_value.__enter__.return_value = client

    result = runner.invoke(app, ["project", "issues", "--owner", "my-org", "--project-id", "1"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"] == [
        {"column": {"id": 5, "title": "Column 5"}, "issues": todo_issues},
        {"column": {"id": 6, "title": "Column 6"}, "issues": []},
        {"column": {"id": 7, "title": "Column 7"}, "issues": []},
        {"column": {"id": 8, "title": "Column 8"}, "issues": []},
        {"column": {"id": 9, "title": "Column 9"}, "issues": []},
    ]
    assert payload["metadata"] == {"status_code": 200, "column_count": 5, "issue_count": 5}

    # Both listings stop on the short page, without requesting the page after it.
    assert [call.kwargs["page"] for call in client.project.list_project_columns.call_args_list] == [1, 2, 3]
    assert [
        (call.kwargs["column_id"], call.kwargs["page"])
        for call in client.project.list_project_column_issues.call_args_list
    ] == [(5, 1), (5, 2), (5, 3), (6, 1), (7, 1), (8, 1), (9, 1)]

    # Every request, continuation or not, asks for a full page.
    calls = (
        client.project.list_project_columns.call_args_list + client.project.list_project_column_issues.call_args_list
    )
    assert [call.kwargs["limit"] for call in calls] == [PAGE_SIZE] * len(calls)


def test_collect_all_pages_measures_short_pages_against_the_first_page():
    """A page longer than the first must not make the pages after it look terminal."""
    pages = [
        [{"id": 1}, {"id": 2}],
        [{"id": 3}, {"id": 4}, {"id": 5}],
        [{"id": 6}, {"id": 7}],
        [{"id": 8}],
    ]
    requested: list[int] = []

    def fetch_page(page):
        requested.append(page)
        return (list(pages[page - 1]) if page <= len(pages) else [], {"status_code": 200, "page": page})

    items, metadata = _collect_all_pages(fetch_page)

    assert [item["id"] for item in items] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert requested == [1, 2, 3, 4]
    assert metadata == {"status_code": 200, "page": 4}
