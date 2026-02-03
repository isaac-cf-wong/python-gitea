"""Unit tests for the issue list command."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from gitea.cli.issue.list import list_command


def make_ctx():
    """Create a mock context object."""
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_list_command_calls_execute_and_wires_params(mock_gitea, mock_get_auth_params, mock_execute):
    """list_command should lookup auth and pass an api_call that calls list_issues with correct params."""
    ctx = make_ctx()

    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.list_issues.return_value = ({"items": []}, {"meta": 1})
    mock_gitea.return_value.__enter__.return_value = client

    since = datetime(2020, 1, 1)

    list_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        state="open",
        labels=["bug"],
        search_string="fix",
        issue_type="issues",
        milestones=["1", "2"],
        since=since,
        before=None,
        created_by="alice",
        assigned_by="bob",
        mentioned_by="carol",
        page=2,
        limit=5,
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_get_auth_params.assert_called_once_with(
        config_path="/tmp/config", account_name="acct", token=None, base_url=None
    )
    mock_execute.assert_called_once()

    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli issue list"

    # Execute the passed api_call and ensure it delegates to the Gitea client
    result = call_kwargs["api_call"]()
    assert result == ({"items": []}, {"meta": 1})

    client.issue.list_issues.assert_called_once_with(
        owner="owner",
        repository="repo",
        state="open",
        labels=["bug"],
        search_string="fix",
        issue_type="issues",
        milestones=[1, 2],
        since=since,
        before=None,
        created_by="alice",
        assigned_by="bob",
        mentioned_by="carol",
        page=2,
        limit=5,
    )
