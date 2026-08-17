"""Unit tests for the issue dependency CLI commands."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from gitea.cli.issue.dependency.add import add_command
from gitea.cli.issue.dependency.list import list_command
from gitea.cli.issue.dependency.remove import remove_command


def make_ctx():
    """Create a mock context object."""
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_add_command(mock_gitea, mock_get_auth_params, mock_execute):
    """add_command should wire auth and call create_issue_dependency."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.create_issue_dependency.return_value = ({"id": 5}, {"status_code": 201})
    mock_gitea.return_value.__enter__.return_value = client

    add_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        issue_id=5,
        dependency_owner="other",
        dependency_repository="other_repo",
        dependency_issue_id=7,
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_get_auth_params.assert_called_once_with(
        config_path="/tmp/config", account_name="acct", token=None, base_url=None
    )
    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli issue dependency add"

    result = call_kwargs["api_call"]()
    client.issue.create_issue_dependency.assert_called_once_with(
        owner="owner",
        repository="repo",
        index=5,
        dependency_owner="other",
        dependency_repository="other_repo",
        dependency_index=7,
    )
    assert result == ({"id": 5}, {"status_code": 201})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_list_command(mock_gitea, mock_get_auth_params, mock_execute):
    """list_command should wire auth and call list_issue_dependencies."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.list_issue_dependencies.return_value = ([{"id": 10}], {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    list_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        issue_id=5,
        page=1,
        limit=20,
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli issue dependency list"

    result = call_kwargs["api_call"]()
    client.issue.list_issue_dependencies.assert_called_once_with(
        owner="owner",
        repository="repo",
        index=5,
        page=1,
        limit=20,
    )
    assert result == ([{"id": 10}], {"status_code": 200})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_remove_command(mock_gitea, mock_get_auth_params, mock_execute):
    """remove_command should wire auth and call remove_issue_dependency."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.remove_issue_dependency.return_value = ({"id": 5}, {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    remove_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        issue_id=5,
        dependency_owner="other",
        dependency_repository="other_repo",
        dependency_issue_id=7,
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli issue dependency remove"

    result = call_kwargs["api_call"]()
    client.issue.remove_issue_dependency.assert_called_once_with(
        owner="owner",
        repository="repo",
        index=5,
        dependency_owner="other",
        dependency_repository="other_repo",
        dependency_index=7,
    )
    assert result == ({"id": 5}, {"status_code": 200})
