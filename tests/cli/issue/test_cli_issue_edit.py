"""Unit tests for the issue edit command."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from gitea.cli.issue.edit import edit_command


def make_ctx():
    """Create a mock context object."""
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_edit_command_calls_execute_and_passes_params(mock_gitea, mock_get_auth_params, mock_execute):
    """edit_command should lookup auth and pass an api_call that calls edit_issue with correct params."""
    ctx = make_ctx()

    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.edit_issue.return_value = ({"id": 1}, {"meta": True})
    mock_gitea.return_value.__enter__.return_value = client

    due = datetime(2021, 5, 1)

    edit_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        index=3,
        assignee="john",
        assignees=["john", "jane"],
        body="Updated",
        due_date=due,
        milestone=7,
        ref="refs/heads/main",
        state="closed",
        title="Title",
        unset_due_date=False,
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_get_auth_params.assert_called_once_with(
        config_path="/tmp/config", account_name="acct", token=None, base_url=None
    )
    mock_execute.assert_called_once()

    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli issue edit"

    # Execute the passed api_call to ensure delegation
    result = call_kwargs["api_call"]()
    assert result == ({"id": 1}, {"meta": True})

    client.issue.edit_issue.assert_called_once_with(
        owner="owner",
        repository="repo",
        index=3,
        assignee="john",
        assignees=["john", "jane"],
        body="Updated",
        due_date=due,
        milestone=7,
        ref="refs/heads/main",
        state="closed",
        title="Title",
        unset_due_date=False,
    )
