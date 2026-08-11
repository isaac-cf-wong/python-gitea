"""Unit tests for the label delete command."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from gitea.cli.label.delete import delete_command


def make_ctx():
    """Create a mock context object."""
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_delete_command_calls_execute_and_wires_params(mock_gitea, mock_get_auth_params, mock_execute):
    """delete_command should lookup auth and pass an api_call that deletes a label."""
    ctx = make_ctx()

    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.label.delete_label.return_value = ({}, {"status_code": 204})
    mock_gitea.return_value.__enter__.return_value = client

    delete_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        label_id=1,
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_get_auth_params.assert_called_once_with(
        config_path="/tmp/config", account_name="acct", token=None, base_url=None
    )
    mock_execute.assert_called_once()

    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli label delete"

    result = call_kwargs["api_call"]()
    client.label.delete_label.assert_called_once_with(owner="owner", repository="repo", label_id=1)
    assert result == ({}, {"status_code": 204})
