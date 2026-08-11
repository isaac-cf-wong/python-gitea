"""Unit tests for the milestone list command."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from gitea.cli.milestone.list import list_command


def make_ctx():
    """Create a mock context object."""
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_list_command_calls_execute_and_wires_params(mock_gitea, mock_get_auth_params, mock_execute):
    """list_command should lookup auth and pass an api_call that lists milestones."""
    ctx = make_ctx()

    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.milestone.list_milestones.return_value = ([{"id": 1, "title": "v1.0"}], {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    list_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        state="open",
        name="v1",
        page=1,
        limit=10,
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_get_auth_params.assert_called_once_with(
        config_path="/tmp/config", account_name="acct", token=None, base_url=None
    )
    mock_execute.assert_called_once()

    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli milestone list"

    result = call_kwargs["api_call"]()
    client.milestone.list_milestones.assert_called_once_with(
        owner="owner", repository="repo", state="open", name="v1", page=1, limit=10
    )
    assert result == ([{"id": 1, "title": "v1.0"}], {"status_code": 200})
