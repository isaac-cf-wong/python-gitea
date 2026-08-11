"""Unit tests for the milestone create command."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from gitea.cli.milestone.create import create_command


def make_ctx():
    """Create a mock context object."""
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_create_command_calls_execute_and_wires_params(mock_gitea, mock_get_auth_params, mock_execute):
    """create_command should lookup auth and pass an api_call that creates a milestone."""
    ctx = make_ctx()

    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.milestone.create_milestone.return_value = ({"id": 1, "title": "v1.0"}, {"status_code": 201})
    mock_gitea.return_value.__enter__.return_value = client

    due_on = datetime(2024, 12, 31)

    create_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        title="v1.0",
        description="First release",
        due_on=due_on,
        state="open",
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_get_auth_params.assert_called_once_with(
        config_path="/tmp/config", account_name="acct", token=None, base_url=None
    )
    mock_execute.assert_called_once()

    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli milestone create"

    result = call_kwargs["api_call"]()
    client.milestone.create_milestone.assert_called_once_with(
        owner="owner",
        repository="repo",
        title="v1.0",
        description="First release",
        due_on=due_on,
        state="open",
    )
    assert result == ({"id": 1, "title": "v1.0"}, {"status_code": 201})
