"""Unit tests for the project CLI commands."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from requests import ConnectionError as RequestsConnectionError
from requests import HTTPError, RequestException
from typer.testing import CliRunner

from gitea.cli.main import app
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
from tests.board import paged_columns, paged_issues
from tests.cli.rendering import unrendered
from tests.transport import RoutedSession

runner = CliRunner()

# The three project issue commands, with the project call each one makes and
# the keyword arguments that call takes beyond the ones they all share.
ISSUE_COMMANDS = [
    pytest.param(add_issue_command, "add_issue_to_project_column", {"column_id": 5}, 201, id="add"),
    pytest.param(move_issue_command, "move_project_issue", {"column_id": 6, "sorting": None}, 204, id="move"),
    pytest.param(remove_issue_command, "remove_issue_from_project_column", {"column_id": 5}, 204, id="remove"),
]


def make_ctx():
    """Create a mock context object."""
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


def board(client, cards, *, project_id=1):
    """Answer the client's board listings with the given columns and the cards on them.

    `project issue move` finds the issue's card before moving it, so a client
    standing in for the instance has to describe a board and not only answer the
    move: a `MagicMock` whose listings answer with mocks describes none.

    Args:
        client: The mock client to attach the listings to.
        cards: Mapping of column ID to the global IDs of the issues carded in it.
        project_id: The project the columns belong to.

    """
    client.project.list_project_columns.side_effect = paged_columns(
        {project_id: [[{"id": column_id} for column_id in cards]]}
    )
    client.project.list_project_column_issues.side_effect = paged_issues(
        {column_id: [[{"id": issue_id} for issue_id in issue_ids]] for column_id, issue_ids in cards.items()}
    )


# The column a card starts in, which is never the column the commands under test
# move it to: a move within one column would pass whether or not it was made.
CARDED_COLUMN = 5


def carded(client, issue_id, *, project_id=1):
    """Answer the board listings with a project one column of which holds the issue's card.

    Args:
        client: The mock client to attach the listings to.
        issue_id: The global ID of the issue whose card is on the board.
        project_id: The project holding the card.

    """
    board(client, {CARDED_COLUMN: (issue_id,)}, project_id=project_id)


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
    carded(client, 1854)
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
    carded(client, 1854)
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
    carded(client, 1854)
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
    carded(client, 1877)
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


@pytest.mark.parametrize(("command", "method", "call_kwargs", "status_code"), ISSUE_COMMANDS)
@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_issue_command_issue_repository_overrides_repository(
    mock_gitea, mock_get_auth_params, mock_execute, command, method, call_kwargs, status_code
):
    """Each issue command should resolve against --issue-repository when it differs from --repository."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1877, "number": 38}, {"status_code": 200})
    getattr(client.project, method).return_value = ({}, {"status_code": status_code})
    carded(client, 1877)
    mock_gitea.return_value.__enter__.return_value = client

    command(
        ctx=ctx,
        owner="owner",
        repository="board-repo",
        issue_repository="other-repo",
        project_id=1,
        issue_id=38,
        account_name="acct",
        token=None,
        base_url=None,
        **call_kwargs,
    )

    result = mock_execute.call_args[1]["api_call"]()
    # The number is looked up in the repository holding the issue, while the
    # project call keeps the repository holding the board.
    client.issue.get_issue.assert_called_once_with(owner="owner", repository="other-repo", index=38)
    getattr(client.project, method).assert_called_once_with(
        owner="owner", repository="board-repo", project_id=1, issue_id=1877, **call_kwargs
    )
    assert result == ({}, {"status_code": status_code, "resolved_issue_id": 1877})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command_org_failure_suggests_issue_repository(mock_gitea, mock_get_auth_params, mock_execute):
    """move_issue_command should point at --issue-repository when a global ID is refused."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.move_project_issue.side_effect = make_http_error(404)
    carded(client, 38)
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


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        pytest.param(make_http_error(404), ("The issue was found in", "owner/repo"), id="refused"),
        pytest.param(
            RequestsConnectionError("Failed to establish a new connection: [Errno 111] Connection refused"),
            ("Could not reach the Gitea API", "https://gitea.example.com"),
            id="unreachable",
        ),
    ],
)
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_reports_failures_without_a_traceback(
    mock_gitea, mock_get_auth_params, monkeypatch, tmp_path, error, expected
):
    """The command should exit 1 with the message alone, through the real logging handler."""
    # Keep the message on one line so the layout stays the simple one, whichever
    # width the terminal running the tests reports.
    monkeypatch.setenv("COLUMNS", "300")
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.base_url = "https://gitea.example.com"
    client.issue.get_issue.return_value = ({"id": 1877, "number": 38}, {"status_code": 200})
    client.project.move_project_issue.side_effect = error
    carded(client, 1877)
    mock_gitea.return_value.__enter__.return_value = client

    result = runner.invoke(
        app,
        [
            # Point at a path of its own so a regression cannot read the
            # developer's own configuration instead.
            "--config-path",
            str(tmp_path / "config.yaml"),
            "project",
            "issue",
            "move",
            "--owner",
            "owner",
            "--repository",
            "repo",
            "--project-id",
            "1",
            "--issue-id",
            "38",
            "--column-id",
            "6",
        ],
    )

    assert result.exit_code == 1
    assert result.stdout == ""
    # `RichHandler` renders the record for whatever terminal it believes it is
    # writing to: it styles the URL inside the message, pads the message column
    # and appends the emitting frame. Assert on the wording each part of the
    # message contributes, over the unstyled text, so none of those decisions
    # can turn a correct message into a failure.
    message = unrendered(result.stderr)
    for fragment in expected:
        assert unrendered(fragment) in message
    # The message is the whole error: no traceback, and none of the wording the
    # unhandled-exception path would add.
    assert "Traceback" not in result.stderr
    assert unrendered("Error executing") not in message


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command_reports_an_issue_with_no_card(mock_gitea, mock_get_auth_params, mock_execute):
    """move_issue_command should refuse to move an issue that has no card on the project.

    Gitea's move endpoint moves the row relating the issue to the project, and
    an issue that is not on the project has none: the call comes back `200` with
    an empty body having moved nothing, so a caller reading the status believes a
    card is on a board that has none. The move is therefore not attempted at all.
    """
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1854, "number": 100}, {"status_code": 200})
    # What the endpoint really answers a move of an uncarded issue with: a
    # success and an empty body, having moved nothing. Answering it here is what
    # makes this test about the no-op rather than about an unstubbed call.
    client.project.move_project_issue.return_value = ({}, {"status_code": 200})
    # The board has a column and the column has a card, but not this issue's.
    board(client, {CARDED_COLUMN: (1900,)})
    mock_gitea.return_value.__enter__.return_value = client

    move_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        issue_id=100,
        column_id=6,
        sorting=None,
        account_name="acct",
        token=None,
        base_url=None,
    )

    with pytest.raises(CommandError) as error:
        mock_execute.call_args[1]["api_call"]()

    message = str(error.value)
    # The issue as the user addressed it, and the two ways out: the command that
    # puts an issue on a board, and the option that has this one do it.
    assert "#100 of owner/repo" in message
    assert "global ID 1854" in message
    assert "project issue add" in message
    assert "--add-if-missing" in message
    client.project.move_project_issue.assert_not_called()
    client.project.add_issue_to_project_column.assert_not_called()


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command_adds_the_issue_when_it_has_no_card(mock_gitea, mock_get_auth_params, mock_execute):
    """--add-if-missing should put an uncarded issue in the target column instead of failing."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1854, "number": 100}, {"status_code": 200})
    client.project.add_issue_to_project_column.return_value = ({}, {"status_code": 201})
    client.project.move_project_issue.return_value = ({}, {"status_code": 200})
    board(client, {CARDED_COLUMN: (1900,)})
    mock_gitea.return_value.__enter__.return_value = client

    move_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        issue_id=100,
        column_id=6,
        sorting=None,
        add_if_missing=True,
        account_name="acct",
        token=None,
        base_url=None,
    )

    result = mock_execute.call_args[1]["api_call"]()
    # The column the move was to, which is where the card has to end up: adding
    # it to the column it came from would be the no-op under another name.
    client.project.add_issue_to_project_column.assert_called_once_with(
        owner="owner", repository="repo", project_id=1, column_id=6, issue_id=1854
    )
    client.project.move_project_issue.assert_not_called()
    assert result == ({}, {"status_code": 201, "resolved_issue_id": 1854})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command_moves_a_carded_issue_with_add_if_missing(mock_gitea, mock_get_auth_params, mock_execute):
    """--add-if-missing should not change what happens to an issue that does have a card."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1854, "number": 100}, {"status_code": 200})
    client.project.move_project_issue.return_value = ({}, {"status_code": 204})
    carded(client, 1854)
    mock_gitea.return_value.__enter__.return_value = client

    move_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        issue_id=100,
        column_id=6,
        sorting=2,
        add_if_missing=True,
        account_name="acct",
        token=None,
        base_url=None,
    )

    result = mock_execute.call_args[1]["api_call"]()
    client.project.move_project_issue.assert_called_once_with(
        owner="owner", repository="repo", project_id=1, issue_id=1854, column_id=6, sorting=2
    )
    client.project.add_issue_to_project_column.assert_not_called()
    assert result == ({}, {"status_code": 204, "resolved_issue_id": 1854})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command_refuses_a_sorting_the_add_cannot_carry(mock_gitea, mock_get_auth_params, mock_execute):
    """--sorting should be refused rather than dropped when there is no card and one is added.

    `--sorting` positions a card among the cards already in a column, and the
    endpoint that puts a card on a board takes no position. Accepting the option
    and adding the card anyway would report a request carried out that was not.
    """
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1854, "number": 100}, {"status_code": 200})
    client.project.move_project_issue.return_value = ({}, {"status_code": 200})
    client.project.add_issue_to_project_column.return_value = ({}, {"status_code": 201})
    board(client, {CARDED_COLUMN: (1900,)})
    mock_gitea.return_value.__enter__.return_value = client

    move_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        issue_id=100,
        column_id=6,
        sorting=3,
        add_if_missing=True,
        account_name="acct",
        token=None,
        base_url=None,
    )

    with pytest.raises(CommandError, match="--sorting"):
        mock_execute.call_args[1]["api_call"]()
    client.project.add_issue_to_project_column.assert_not_called()
    client.project.move_project_issue.assert_not_called()


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        pytest.param(make_http_error(403), "Gitea returned HTTP 403", id="refused"),
        pytest.param(
            RequestsConnectionError("Failed to establish a new connection: [Errno 111] Connection refused"),
            "Could not reach the Gitea API",
            id="unreachable",
        ),
        pytest.param(
            RequestException("Invalid URL 'columns': No scheme supplied"),
            "Could not complete the request to the Gitea API",
            id="incomplete",
        ),
    ],
)
@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command_reports_a_board_it_could_not_read(
    mock_gitea, mock_get_auth_params, mock_execute, error, expected
):
    """A board that could not be read should be reported as such, and stop the move.

    The two answers have to stay apart: a lookup that failed says nothing about
    whether the issue has a card, so reporting it as uncarded would be a claim
    the failure does not support, and moving anyway would be the silent no-op the
    lookup is there to prevent.
    """
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.base_url = "https://gitea.example.com"
    client.issue.get_issue.return_value = ({"id": 1854, "number": 100}, {"status_code": 200})
    client.project.move_project_issue.return_value = ({}, {"status_code": 200})
    client.project.list_project_columns.side_effect = error
    mock_gitea.return_value.__enter__.return_value = client

    move_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        issue_id=100,
        column_id=6,
        sorting=None,
        account_name="acct",
        token=None,
        base_url=None,
    )

    with pytest.raises(CommandError) as raised:
        mock_execute.call_args[1]["api_call"]()

    message = str(raised.value)
    assert expected in message
    assert "project issue add" not in message
    client.project.move_project_issue.assert_not_called()
    client.project.add_issue_to_project_column.assert_not_called()


@patch("gitea.client.gitea.requests.Session")
def test_move_issue_sends_no_move_request_for_an_issue_with_no_card(mock_session):
    """No request should reach the move endpoint for an issue the board has no card for.

    The assertions above are made against a client; this one is made against the
    session the real client builds its requests on, so what is pinned is that the
    request Gitea would have answered with a success and a no-op is never sent.
    """
    session = RoutedSession(
        routes=(
            # A column of the board, holding a card - for another issue.
            (f"/columns/{CARDED_COLUMN}/issues", [{"id": 1900}]),
            ("/columns", [{"id": CARDED_COLUMN}]),
        ),
        # What the issue lookup is answered with: the global ID of `#100`.
        payload={"id": 1854, "number": 100},
    )
    mock_session.return_value = session

    result = runner.invoke(
        app,
        [
            "project",
            "issue",
            "move",
            "--owner",
            "owner",
            "--repository",
            "repo",
            "--project-id",
            "1",
            "--column-id",
            "6",
            "--issue-id",
            "100",
            "--token",
            "tok",
            "--base-url",
            "https://gitea.invalid",
        ],
    )

    assert result.exit_code == 1
    assert result.stdout == ""
    assert not [url for url in session.urls if url.endswith("/move")], session.urls
