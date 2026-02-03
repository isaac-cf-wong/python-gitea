"""Unit tests for the CLI user get command."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from gitea.cli.user.get import get_command


def make_ctx():
    """Create a mock Typer context with config_path."""
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_get_command_calls_execute_and_uses_auth(mock_gitea, mock_get_auth_params, mock_execute):
    """get_command should lookup auth and pass an api_call to execute_api_command."""
    ctx = make_ctx()

    # Configure get_auth_params to return token and base_url
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    # Configure the Gitea context manager to return a client whose user.get_user returns data
    client = MagicMock()
    client.user.get_user.return_value = ({"id": 1}, {"meta": "x"})
    mock_gitea.return_value.__enter__.return_value = client

    # Call the command
    get_command(ctx=ctx, username="bob", account_name="acct", token=None, base_url=None)

    # get_auth_params should be called with ctx.obj config_path and provided args
    mock_get_auth_params.assert_called_once_with(
        config_path="/tmp/config", account_name="acct", token=None, base_url=None
    )

    # execute_api_command should be called with a callable api_call and correct command name
    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    assert "api_call" in call_kwargs
    assert call_kwargs["command_name"] == "gitea-cli user get"

    # Execute the api_call and ensure it uses the Gitea client
    result = call_kwargs["api_call"]()
    assert result == ({"id": 1}, {"meta": "x"})
    client.user.get_user.assert_called_once_with(username="bob")


def test_get_command_defaults_to_none_for_username():
    """If username is not provided, api_call should call get_user with username=None."""
    ctx = make_ctx()

    with (
        patch("gitea.cli.utils.api.execute_api_command") as mock_execute,
        patch("gitea.cli.utils.auth.get_auth_params", return_value=("t", "u")),
    ):
        client = MagicMock()
        client.user.get_user.return_value = ({"id": 2}, {})
        with patch("gitea.client.gitea.Gitea") as mock_gitea:
            mock_gitea.return_value.__enter__.return_value = client
            get_command(ctx=ctx)

            call_kwargs = mock_execute.call_args[1]
            # Call the api_call and ensure username passed through is None
            result = call_kwargs["api_call"]()
            assert result == ({"id": 2}, {})
            client.user.get_user.assert_called_once_with(username=None)
