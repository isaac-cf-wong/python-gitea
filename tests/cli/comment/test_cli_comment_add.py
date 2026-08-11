"""Unit tests for the comment add command."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from gitea.cli.comment.add import add_command


def make_ctx():
    """Create a mock context object."""
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_add_command_calls_execute_and_wires_params(mock_gitea, mock_get_auth_params, mock_execute):
    """add_command should lookup auth and pass an api_call that creates a comment."""
    ctx = make_ctx()

    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.comment.create_comment.return_value = ({"id": 1, "body": "Hello"}, {"status_code": 201})
    mock_gitea.return_value.__enter__.return_value = client

    add_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        index=7,
        body="Hello",
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_get_auth_params.assert_called_once_with(
        config_path="/tmp/config", account_name="acct", token=None, base_url=None
    )
    mock_execute.assert_called_once()

    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli comment add"

    result = call_kwargs["api_call"]()
    client.comment.create_comment.assert_called_once_with(owner="owner", repository="repo", index=7, body="Hello")
    assert result == ({"id": 1, "body": "Hello"}, {"status_code": 201})
