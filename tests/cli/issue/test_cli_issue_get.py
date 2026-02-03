"""Unit tests for the issue get command."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from gitea.cli.issue.get import get_command


def make_ctx():
    """Create a mock context object."""
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_get_command_calls_execute_and_delegates(mock_gitea, mock_get_auth_params, mock_execute):
    """get_command should lookup auth and pass an api_call that calls get_issue with correct params."""
    ctx = make_ctx()

    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 10}, {"meta": 2})
    mock_gitea.return_value.__enter__.return_value = client

    get_command(ctx=ctx, owner="owner", repository="repo", index=5, account_name="acct", token=None, base_url=None)

    mock_get_auth_params.assert_called_once_with(
        config_path="/tmp/config", account_name="acct", token=None, base_url=None
    )
    mock_execute.assert_called_once()

    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli issue get"

    result = call_kwargs["api_call"]()
    assert result == ({"id": 10}, {"meta": 2})
    client.issue.get_issue.assert_called_once_with(owner="owner", repository="repo", index=5)
