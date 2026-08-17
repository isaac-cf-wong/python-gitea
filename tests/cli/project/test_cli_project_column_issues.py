"""Unit tests for the project column-issue listing CLI commands."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from gitea.cli.main import app
from gitea.cli.project.column.issues import list_column_issues_command
from gitea.cli.project.issues import list_project_issues_command

runner = CliRunner()

ISSUES = [
    {"number": 7, "title": "Fix the docs", "state": "open"},
    {"number": 9, "title": "Ship the release", "state": "closed"},
]


def make_ctx():
    """Create a mock context object."""
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


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
    client.project.list_project_columns.return_value = (
        [{"id": 5, "title": "Todo"}, {"id": 6, "title": "Done"}],
        {"status_code": 200},
    )
    client.project.list_project_column_issues.side_effect = [
        (ISSUES[:1], {"status_code": 200}),
        (ISSUES[1:], {"status_code": 200}),
    ]
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
    client.project.list_project_columns.assert_called_once_with(owner="owner", repository="repo", project_id=1)
    assert [call.kwargs["column_id"] for call in client.project.list_project_column_issues.call_args_list] == [5, 6]
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
    client.project.list_project_columns.return_value = ([{"id": 5, "title": "Todo"}], {"status_code": 200})
    client.project.list_project_column_issues.return_value = (ISSUES, {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    list_project_issues_command(ctx=ctx, owner="my-org", project_id=1)

    call_kwargs = mock_execute.call_args[1]
    call_kwargs["api_call"]()
    client.project.list_project_columns.assert_called_once_with(owner="my-org", repository=None, project_id=1)
    client.project.list_project_column_issues.assert_called_once_with(
        owner="my-org", repository=None, project_id=1, column_id=5
    )


@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_list_project_issues_output_envelope(mock_gitea, mock_get_auth_params):
    """`project issues` should print the grouped cards in the standard JSON envelope."""
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.list_project_columns.return_value = ([{"id": 5, "title": "Todo"}], {"status_code": 200})
    client.project.list_project_column_issues.return_value = (ISSUES, {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    result = runner.invoke(app, ["project", "issues", "--owner", "my-org", "--project-id", "1"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload == {
        "data": [{"column": {"id": 5, "title": "Todo"}, "issues": ISSUES}],
        "metadata": {"status_code": 200, "column_count": 1, "issue_count": 2},
    }
