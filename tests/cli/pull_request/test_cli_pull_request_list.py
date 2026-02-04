"""Unit tests for the pull-request list command."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from gitea.cli.pull_request.list import list_command


def make_ctx():
    """Create a mock Typer context with config_path."""
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_list_command_calls_execute_and_delegates(mock_gitea, mock_get_auth_params, mock_execute):
    """list_command should lookup auth and pass an api_call that calls list_pull_requests."""
    ctx = make_ctx()

    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.pull_request.list_pull_requests.return_value = ([{"id": 1}], {"meta": 1})
    mock_gitea.return_value.__enter__.return_value = client

    list_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        base_branch="main",
        state="open",
        sort="recentupdate",
        milestone=5,
        labels=[1, 2],
        poster="user",
        page=3,
        limit=15,
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_get_auth_params.assert_called_once_with(
        config_path="/tmp/config", account_name="acct", token=None, base_url=None
    )
    mock_execute.assert_called_once()

    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli pull-request list"

    # Execute the passed api_call and ensure it delegates to the Gitea client
    result = call_kwargs["api_call"]()
    assert result == ([{"id": 1}], {"meta": 1})

    client.pull_request.list_pull_requests.assert_called_once_with(
        owner="owner",
        repository="repo",
        base_branch="main",
        state="open",
        sort="recentupdate",
        milestone=5,
        labels=[1, 2],
        poster="user",
        page=3,
        limit=15,
    )
