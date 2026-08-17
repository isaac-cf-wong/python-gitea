"""Unit tests for the issue get command."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from gitea.cli.issue.get import get_command, rename_comment_count


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


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_get_command_renames_comments_to_comment_count(mock_gitea, mock_get_auth_params, mock_execute):
    """get_command should expose the API's `comments` count as `comment_count`."""
    ctx = make_ctx()

    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 10, "comments": 3, "title": "Bug"}, {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    get_command(ctx=ctx, owner="owner", repository="repo", index=5, account_name="acct", token=None, base_url=None)

    data, metadata = mock_execute.call_args[1]["api_call"]()
    assert data == {"id": 10, "comment_count": 3, "title": "Bug"}
    assert "comments" not in data
    assert metadata == {"status_code": 200}


def test_rename_comment_count_renames_in_place():
    """The `comments` key should be renamed while keeping its value and position."""
    issue = {"id": 1, "comments": 7, "title": "Bug"}

    result = rename_comment_count(issue)

    assert list(result.items()) == [("id", 1), ("comment_count", 7), ("title", "Bug")]


def test_rename_comment_count_without_comments_field():
    """An issue without a `comments` key should be returned unchanged."""
    issue = {"id": 1, "title": "Bug"}

    assert rename_comment_count(issue) == {"id": 1, "title": "Bug"}
