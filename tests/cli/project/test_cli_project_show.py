"""Unit tests for `project show`, the board in one call."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from gitea.cli.main import app
from gitea.cli.project.show import show_command
from gitea.utils.pagination import PAGE_SIZE

runner = CliRunner()

PROJECT = {"id": 31, "title": "Board", "state": "open", "type": "organization", "repo_id": 0}

# The global ID and the number differ on every issue here: `issue_ids` reports
# the global ID the project endpoints take, and a test whose issues had the two
# the same would pass just as well if the command reported the number.
ISSUES = [
    {"id": 1873, "number": 7, "title": "Fix the docs", "state": "open"},
    {"id": 1874, "number": 9, "title": "Ship the release", "state": "closed"},
]

# A column as the endpoint answers with one, rather than the id and title the
# command needs: the fields beyond those two are the ones a projection would
# drop, and the assertions below are what notices if one starts doing so.
COLUMNS = [
    {"id": 5, "title": "Todo", "default": True, "sorting": 0, "project_id": 31},
    {"id": 6, "title": "Done", "default": False, "sorting": 1, "project_id": 31},
]


def make_ctx():
    """Create a mock context object.

    Returns:
        The context the command reads its configuration path from.

    """
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


def paged_columns(*pages, metadata=None):
    """Build a side effect serving one page of columns per requested page number.

    Args:
        *pages: The columns of each page, in order.
        metadata: The metadata every page carries. Defaults to a successful call.

    Returns:
        A side effect returning the requested page, or an empty page beyond the last one.

    """
    page_metadata = {"status_code": 200} if metadata is None else metadata

    def _side_effect(**kwargs):
        page = kwargs.get("page", 1)
        return (list(pages[page - 1]) if page <= len(pages) else [], page_metadata)

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


def make_client(mock_gitea, *, columns=None, issues_by_column=None, project_metadata=None):
    """Build the client a `project show` invocation is answered by.

    Args:
        mock_gitea: The patched client class, whose context manager is wired to
            the client built here.
        columns: The single page of columns the board holds. Defaults to `COLUMNS`.
        issues_by_column: Mapping of column ID to that column's pages of issues.
            Defaults to one issue on the first column and one on the second.
        project_metadata: The metadata the project fetch answers with.

    Returns:
        The mock client.

    """
    client = MagicMock()
    client.project.get_project.return_value = (
        PROJECT,
        {"status_code": 200} if project_metadata is None else project_metadata,
    )
    client.project.list_project_columns.side_effect = paged_columns(COLUMNS if columns is None else columns)
    client.project.list_project_column_issues.side_effect = paged_issues(
        {5: [ISSUES[:1]], 6: [ISSUES[1:]]} if issues_by_column is None else issues_by_column
    )
    mock_gitea.return_value.__enter__.return_value = client
    return client


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_show_command(mock_gitea, mock_get_auth_params, mock_execute):
    """`project show` should report the project, its columns, and each column's cards."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")
    client = make_client(mock_gitea)

    show_command(
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
    assert call_kwargs["command_name"] == "gitea-cli project show"

    data, metadata = call_kwargs["api_call"]()

    client.project.get_project.assert_called_once_with(owner="owner", repository="repo", project_id=1)
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

    assert data == {
        "project": PROJECT,
        "columns": [
            {**COLUMNS[0], "issue_count": 1, "issue_ids": [1873]},
            {**COLUMNS[1], "issue_count": 1, "issue_ids": [1874]},
        ],
    }
    assert metadata == {"status_code": 200, "column_count": 2, "issue_count": 2}


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_show_command_without_full_omits_the_issues_themselves(mock_gitea, mock_get_auth_params, mock_execute):
    """Without `--full` a column should carry the IDs of its cards and not the cards."""
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")
    make_client(mock_gitea)

    show_command(ctx=make_ctx(), owner="my-org", project_id=1)

    data, _ = mock_execute.call_args[1]["api_call"]()

    for column in data["columns"]:
        assert "issues" not in column


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_show_command_full_includes_every_card(mock_gitea, mock_get_auth_params, mock_execute):
    """`--full` should add each column's issues, as the API returned them."""
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")
    make_client(mock_gitea)

    show_command(ctx=make_ctx(), owner="my-org", project_id=1, full=True)

    data, metadata = mock_execute.call_args[1]["api_call"]()

    assert data == {
        "project": PROJECT,
        "columns": [
            {**COLUMNS[0], "issue_count": 1, "issue_ids": [1873], "issues": ISSUES[:1]},
            {**COLUMNS[1], "issue_count": 1, "issue_ids": [1874], "issues": ISSUES[1:]},
        ],
    }
    assert metadata == {"status_code": 200, "column_count": 2, "issue_count": 2}


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_show_command_organization_project(mock_gitea, mock_get_auth_params, mock_execute):
    """Omitting the repository should ask for the owner's own project throughout."""
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")
    client = make_client(mock_gitea)

    show_command(ctx=make_ctx(), owner="my-org", project_id=1)

    mock_execute.call_args[1]["api_call"]()

    client.project.get_project.assert_called_once_with(owner="my-org", repository=None, project_id=1)
    calls = (
        client.project.list_project_columns.call_args_list + client.project.list_project_column_issues.call_args_list
    )
    assert [call.kwargs["repository"] for call in calls] == [None] * len(calls)
    assert [call.kwargs["owner"] for call in calls] == ["my-org"] * len(calls)


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_show_command_reports_the_project_calls_status(mock_gitea, mock_get_auth_params, mock_execute):
    """The status code reported should be the project fetch's, not a listing's.

    The project is what the command was asked for; the columns and their issues
    describe it. The listings answer 200 here and the project answers 203, so a
    command reporting the wrong call's status is visible.
    """
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")
    make_client(mock_gitea, project_metadata={"status_code": 203, "url": "https://gitea.example.com/projects/1"})

    show_command(ctx=make_ctx(), owner="my-org", project_id=1)

    _, metadata = mock_execute.call_args[1]["api_call"]()

    assert metadata == {
        "status_code": 203,
        "url": "https://gitea.example.com/projects/1",
        "column_count": 2,
        "issue_count": 2,
    }


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_show_command_empty_board(mock_gitea, mock_get_auth_params, mock_execute):
    """A board without columns should report no columns and no cards."""
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")
    client = make_client(mock_gitea, columns=[], issues_by_column={})

    show_command(ctx=make_ctx(), owner="my-org", project_id=1)

    data, metadata = mock_execute.call_args[1]["api_call"]()

    assert data == {"project": PROJECT, "columns": []}
    assert metadata == {"status_code": 200, "column_count": 0, "issue_count": 0}
    client.project.list_project_column_issues.assert_not_called()


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_show_command_empty_column(mock_gitea, mock_get_auth_params, mock_execute):
    """A column holding no cards should report a count of zero and no IDs."""
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")
    make_client(mock_gitea, issues_by_column={5: [ISSUES], 6: []})

    show_command(ctx=make_ctx(), owner="my-org", project_id=1)

    data, metadata = mock_execute.call_args[1]["api_call"]()

    assert data["columns"] == [
        {**COLUMNS[0], "issue_count": 2, "issue_ids": [1873, 1874]},
        {**COLUMNS[1], "issue_count": 0, "issue_ids": []},
    ]
    assert metadata["issue_count"] == 2


@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_show_output_envelope(mock_gitea, mock_get_auth_params):
    """`project show` should print the board in the standard JSON envelope."""
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")
    make_client(mock_gitea)

    result = runner.invoke(app, ["project", "show", "--owner", "my-org", "--project-id", "31"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload == {
        "data": {
            "project": PROJECT,
            "columns": [
                {**COLUMNS[0], "issue_count": 1, "issue_ids": [1873]},
                {**COLUMNS[1], "issue_count": 1, "issue_ids": [1874]},
            ],
        },
        "metadata": {"status_code": 200, "column_count": 2, "issue_count": 2},
    }


@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_show_full_flag_is_accepted_on_the_command_line(mock_gitea, mock_get_auth_params):
    """`--full` should be a flag, and should widen what each column carries."""
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")
    make_client(mock_gitea)

    result = runner.invoke(app, ["project", "show", "--owner", "my-org", "--project-id", "31", "--full"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert [column["issues"] for column in payload["data"]["columns"]] == [ISSUES[:1], ISSUES[1:]]


@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_show_spans_every_page(mock_gitea, mock_get_auth_params):
    """Every page of columns, and of each column's issues, should be counted."""
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    columns = [{"id": column_id, "title": f"Column {column_id}"} for column_id in (5, 6, 7)]
    todo_issues = [{"id": 100 + n, "number": n, "title": f"Issue {n}"} for n in (1, 2, 3)]
    doing_issues = [{"id": 104, "number": 4, "title": "Issue 4"}]

    client = MagicMock()
    client.project.get_project.return_value = (PROJECT, {"status_code": 200})
    client.project.list_project_columns.side_effect = paged_columns(columns[:2], columns[2:])
    client.project.list_project_column_issues.side_effect = paged_issues(
        {5: [todo_issues[:2], todo_issues[2:]], 6: [doing_issues], 7: []}
    )
    mock_gitea.return_value.__enter__.return_value = client

    result = runner.invoke(app, ["project", "show", "--owner", "my-org", "--project-id", "31"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["columns"] == [
        {**columns[0], "issue_count": 3, "issue_ids": [101, 102, 103]},
        {**columns[1], "issue_count": 1, "issue_ids": [104]},
        {**columns[2], "issue_count": 0, "issue_ids": []},
    ]
    assert payload["metadata"] == {"status_code": 200, "column_count": 3, "issue_count": 4}
    assert [call.kwargs["page"] for call in client.project.list_project_columns.call_args_list] == [1, 2]
    assert [
        (call.kwargs["column_id"], call.kwargs["page"])
        for call in client.project.list_project_column_issues.call_args_list
    ] == [(5, 1), (5, 2), (6, 1), (6, 2), (7, 1)]


@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_show_reports_a_failure_without_a_traceback(mock_gitea, mock_get_auth_params):
    """A refused call should exit non-zero having printed nothing on stdout."""
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.get_project.side_effect = RuntimeError("refused")
    mock_gitea.return_value.__enter__.return_value = client

    result = runner.invoke(app, ["project", "show", "--owner", "my-org", "--project-id", "31"])

    assert result.exit_code == 1
    assert result.stdout == ""
