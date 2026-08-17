"""Unit tests for the project CLI commands."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from requests import HTTPError

from gitea.cli.project.column.create import create_column_command
from gitea.cli.project.column.list import list_columns_command
from gitea.cli.project.create import create_command
from gitea.cli.project.delete import delete_command
from gitea.cli.project.edit import edit_command
from gitea.cli.project.get import get_command
from gitea.cli.project.issue.add import add_issue_command
from gitea.cli.project.issue.move import move_issue_command
from gitea.cli.project.issue.remove import remove_issue_command
from gitea.cli.project.list import list_command
from gitea.cli.utils.errors import CommandError


def make_ctx():
    """Create a mock context object."""
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


def make_http_error(status_code):
    """Create the error the client raises for an unsuccessful response.

    Args:
        status_code: The status code the response carries.

    Returns:
        The HTTP error.

    """
    response = MagicMock()
    response.status_code = status_code
    return HTTPError(f"{status_code} Client Error", response=response)


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_create_command(mock_gitea, mock_get_auth_params, mock_execute):
    """create_command should wire auth and call create_project."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.create_project.return_value = ({"id": 1, "title": "Board"}, {"status_code": 201})
    mock_gitea.return_value.__enter__.return_value = client

    create_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        title="Board",
        description="desc",
        template_type="basic_kanban",
        card_type="text_only",
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli project create"

    result = call_kwargs["api_call"]()
    client.project.create_project.assert_called_once_with(
        owner="owner",
        repository="repo",
        title="Board",
        description="desc",
        template_type="basic_kanban",
        card_type="text_only",
    )
    assert result == ({"id": 1, "title": "Board"}, {"status_code": 201})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_list_command(mock_gitea, mock_get_auth_params, mock_execute):
    """list_command should wire auth and call list_projects."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.list_projects.return_value = ([{"id": 1}], {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    list_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        state="open",
        page=1,
        limit=10,
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli project list"

    result = call_kwargs["api_call"]()
    client.project.list_projects.assert_called_once_with(
        owner="owner", repository="repo", state="open", page=1, limit=10
    )
    assert result == ([{"id": 1}], {"status_code": 200})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_list_command_org(mock_gitea, mock_get_auth_params, mock_execute):
    """list_command should pass repository=None for organization projects."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.list_projects.return_value = ([{"id": 27}], {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    list_command(
        ctx=ctx,
        owner="org",
        repository=None,
        state=None,
        page=None,
        limit=None,
        account_name="acct",
        token=None,
        base_url=None,
    )

    result = mock_execute.call_args[1]["api_call"]()
    client.project.list_projects.assert_called_once_with(
        owner="org", repository=None, state=None, page=None, limit=None
    )
    assert result == ([{"id": 27}], {"status_code": 200})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_get_command(mock_gitea, mock_get_auth_params, mock_execute):
    """get_command should wire auth and call get_project."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.get_project.return_value = ({"id": 1}, {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    get_command(
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
    result = call_kwargs["api_call"]()
    client.project.get_project.assert_called_once_with(owner="owner", repository="repo", project_id=1)
    assert result == ({"id": 1}, {"status_code": 200})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_edit_command(mock_gitea, mock_get_auth_params, mock_execute):
    """edit_command should wire auth and call edit_project."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.edit_project.return_value = ({"id": 1, "title": "Renamed"}, {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    edit_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        title="Renamed",
        description=None,
        card_type=None,
        state="closed",
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli project edit"

    result = call_kwargs["api_call"]()
    client.project.edit_project.assert_called_once_with(
        owner="owner",
        repository="repo",
        project_id=1,
        title="Renamed",
        description=None,
        card_type=None,
        state="closed",
    )
    assert result == ({"id": 1, "title": "Renamed"}, {"status_code": 200})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_delete_command(mock_gitea, mock_get_auth_params, mock_execute):
    """delete_command should wire auth and call delete_project."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.delete_project.return_value = ({}, {"status_code": 204})
    mock_gitea.return_value.__enter__.return_value = client

    delete_command(
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
    result = call_kwargs["api_call"]()
    client.project.delete_project.assert_called_once_with(owner="owner", repository="repo", project_id=1)
    assert result == ({}, {"status_code": 204})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_create_column_command(mock_gitea, mock_get_auth_params, mock_execute):
    """create_column_command should wire auth and call create_project_column."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.create_project_column.return_value = ({"id": 5, "title": "Todo"}, {"status_code": 201})
    mock_gitea.return_value.__enter__.return_value = client

    create_column_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        title="Todo",
        color="#FF0000",
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli project column create"

    result = call_kwargs["api_call"]()
    client.project.create_project_column.assert_called_once_with(
        owner="owner", repository="repo", project_id=1, title="Todo", color="#FF0000"
    )
    assert result == ({"id": 5, "title": "Todo"}, {"status_code": 201})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_list_columns_command(mock_gitea, mock_get_auth_params, mock_execute):
    """list_columns_command should wire auth and call list_project_columns."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.list_project_columns.return_value = ([{"id": 5}], {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    list_columns_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        page=None,
        limit=None,
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli project column list"

    result = call_kwargs["api_call"]()
    client.project.list_project_columns.assert_called_once_with(
        owner="owner", repository="repo", project_id=1, page=None, limit=None
    )
    assert result == ([{"id": 5}], {"status_code": 200})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_add_issue_command(mock_gitea, mock_get_auth_params, mock_execute):
    """add_issue_command should wire auth and call add_issue_to_project_column."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1854, "number": 100}, {"status_code": 200})
    client.project.add_issue_to_project_column.return_value = ({}, {"status_code": 201})
    mock_gitea.return_value.__enter__.return_value = client

    add_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        column_id=5,
        issue_id=100,
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli project issue add"

    result = call_kwargs["api_call"]()
    client.issue.get_issue.assert_called_once_with(owner="owner", repository="repo", index=100)
    client.project.add_issue_to_project_column.assert_called_once_with(
        owner="owner", repository="repo", project_id=1, column_id=5, issue_id=1854
    )
    assert result == ({}, {"status_code": 201, "resolved_issue_id": 1854})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command(mock_gitea, mock_get_auth_params, mock_execute):
    """move_issue_command should wire auth and call move_project_issue."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1854, "number": 100}, {"status_code": 200})
    client.project.move_project_issue.return_value = ({}, {"status_code": 204})
    mock_gitea.return_value.__enter__.return_value = client

    move_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        issue_id=100,
        column_id=6,
        sorting=1,
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli project issue move"

    result = call_kwargs["api_call"]()
    client.issue.get_issue.assert_called_once_with(owner="owner", repository="repo", index=100)
    client.project.move_project_issue.assert_called_once_with(
        owner="owner", repository="repo", project_id=1, issue_id=1854, column_id=6, sorting=1
    )
    assert result == ({}, {"status_code": 204, "resolved_issue_id": 1854})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_remove_issue_command(mock_gitea, mock_get_auth_params, mock_execute):
    """remove_issue_command should wire auth and call remove_issue_from_project_column."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1854, "number": 100}, {"status_code": 200})
    client.project.remove_issue_from_project_column.return_value = ({}, {"status_code": 204})
    mock_gitea.return_value.__enter__.return_value = client

    remove_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        column_id=5,
        issue_id=100,
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli project issue remove"

    result = call_kwargs["api_call"]()
    client.issue.get_issue.assert_called_once_with(owner="owner", repository="repo", index=100)
    client.project.remove_issue_from_project_column.assert_called_once_with(
        owner="owner", repository="repo", project_id=1, column_id=5, issue_id=1854
    )
    assert result == ({}, {"status_code": 204, "resolved_issue_id": 1854})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command_org(mock_gitea, mock_get_auth_params, mock_execute):
    """move_issue_command should pass --issue-id through unresolved for organization projects."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.move_project_issue.return_value = ({}, {"status_code": 204})
    mock_gitea.return_value.__enter__.return_value = client

    move_issue_command(
        ctx=ctx,
        owner="org",
        repository=None,
        project_id=1,
        issue_id=1854,
        column_id=6,
        sorting=None,
        account_name="acct",
        token=None,
        base_url=None,
    )

    result = mock_execute.call_args[1]["api_call"]()
    client.issue.get_issue.assert_not_called()
    client.project.move_project_issue.assert_called_once_with(
        owner="org", repository=None, project_id=1, issue_id=1854, column_id=6, sorting=None
    )
    assert result == ({}, {"status_code": 204})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_add_issue_command_org(mock_gitea, mock_get_auth_params, mock_execute):
    """add_issue_command should pass --issue-id through unresolved for organization projects."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.add_issue_to_project_column.return_value = ({}, {"status_code": 201})
    mock_gitea.return_value.__enter__.return_value = client

    add_issue_command(
        ctx=ctx,
        owner="org",
        repository=None,
        project_id=1,
        column_id=5,
        issue_id=1854,
        account_name="acct",
        token=None,
        base_url=None,
    )

    result = mock_execute.call_args[1]["api_call"]()
    client.issue.get_issue.assert_not_called()
    client.project.add_issue_to_project_column.assert_called_once_with(
        owner="org", repository=None, project_id=1, column_id=5, issue_id=1854
    )
    assert result == ({}, {"status_code": 201})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command_unknown_issue_number(mock_gitea, mock_get_auth_params, mock_execute):
    """move_issue_command should fail loudly when the issue number does not exist."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.side_effect = make_http_error(404)
    mock_gitea.return_value.__enter__.return_value = client

    move_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        issue_id=9999,
        column_id=6,
        sorting=None,
        account_name="acct",
        token=None,
        base_url=None,
    )

    with pytest.raises(CommandError, match="owner/repo"):
        mock_execute.call_args[1]["api_call"]()
    client.project.move_project_issue.assert_not_called()


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command_api_failure(mock_gitea, mock_get_auth_params, mock_execute):
    """move_issue_command should surface a failing API status instead of an empty envelope."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1854, "number": 15}, {"status_code": 200})
    client.project.move_project_issue.side_effect = make_http_error(404)
    mock_gitea.return_value.__enter__.return_value = client

    move_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        issue_id=15,
        column_id=6,
        sorting=None,
        account_name="acct",
        token=None,
        base_url=None,
    )

    with pytest.raises(CommandError, match="HTTP 404"):
        mock_execute.call_args[1]["api_call"]()


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_remove_issue_command_api_failure(mock_gitea, mock_get_auth_params, mock_execute):
    """remove_issue_command should surface a failing API status instead of an empty envelope."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.remove_issue_from_project_column.side_effect = make_http_error(403)
    mock_gitea.return_value.__enter__.return_value = client

    remove_issue_command(
        ctx=ctx,
        owner="org",
        repository=None,
        project_id=1,
        column_id=5,
        issue_id=1854,
        account_name="acct",
        token=None,
        base_url=None,
    )

    with pytest.raises(CommandError, match="HTTP 403"):
        mock_execute.call_args[1]["api_call"]()


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_add_issue_command_api_failure(mock_gitea, mock_get_auth_params, mock_execute):
    """add_issue_command should surface a failing API status instead of an empty envelope."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1854, "number": 15}, {"status_code": 200})
    client.project.add_issue_to_project_column.side_effect = make_http_error(404)
    mock_gitea.return_value.__enter__.return_value = client

    add_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        column_id=5,
        issue_id=15,
        account_name="acct",
        token=None,
        base_url=None,
    )

    with pytest.raises(CommandError, match="HTTP 404"):
        mock_execute.call_args[1]["api_call"]()


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command_org_with_issue_repository(mock_gitea, mock_get_auth_params, mock_execute):
    """move_issue_command should resolve the number against --issue-repository on an organization project."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1877, "number": 38}, {"status_code": 200})
    client.project.move_project_issue.return_value = ({}, {"status_code": 204})
    mock_gitea.return_value.__enter__.return_value = client

    move_issue_command(
        ctx=ctx,
        owner="org",
        repository=None,
        issue_repository="repo",
        project_id=1,
        issue_id=38,
        column_id=6,
        sorting=None,
        account_name="acct",
        token=None,
        base_url=None,
    )

    result = mock_execute.call_args[1]["api_call"]()
    client.issue.get_issue.assert_called_once_with(owner="org", repository="repo", index=38)
    client.project.move_project_issue.assert_called_once_with(
        owner="org", repository=None, project_id=1, issue_id=1877, column_id=6, sorting=None
    )
    assert result == ({}, {"status_code": 204, "resolved_issue_id": 1877})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_add_issue_command_issue_repository_overrides_repository(mock_gitea, mock_get_auth_params, mock_execute):
    """add_issue_command should resolve against --issue-repository when it differs from --repository."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1877, "number": 38}, {"status_code": 200})
    client.project.add_issue_to_project_column.return_value = ({}, {"status_code": 201})
    mock_gitea.return_value.__enter__.return_value = client

    add_issue_command(
        ctx=ctx,
        owner="owner",
        repository="board-repo",
        issue_repository="other-repo",
        project_id=1,
        column_id=5,
        issue_id=38,
        account_name="acct",
        token=None,
        base_url=None,
    )

    result = mock_execute.call_args[1]["api_call"]()
    client.issue.get_issue.assert_called_once_with(owner="owner", repository="other-repo", index=38)
    client.project.add_issue_to_project_column.assert_called_once_with(
        owner="owner", repository="board-repo", project_id=1, column_id=5, issue_id=1877
    )
    assert result == ({}, {"status_code": 201, "resolved_issue_id": 1877})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command_org_failure_suggests_issue_repository(mock_gitea, mock_get_auth_params, mock_execute):
    """move_issue_command should point at --issue-repository when a global ID is refused."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.move_project_issue.side_effect = make_http_error(404)
    mock_gitea.return_value.__enter__.return_value = client

    move_issue_command(
        ctx=ctx,
        owner="org",
        repository=None,
        project_id=1,
        issue_id=38,
        column_id=6,
        sorting=None,
        account_name="acct",
        token=None,
        base_url=None,
    )

    with pytest.raises(CommandError, match="--issue-repository REPOSITORY"):
        mock_execute.call_args[1]["api_call"]()
    client.issue.get_issue.assert_not_called()
