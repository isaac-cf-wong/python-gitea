"""Unit tests for the issue close command."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from gitea.cli.issue.close import close_command


def make_ctx():
    """Create a mock context object."""
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_close_command_calls_execute_and_passes_params(mock_gitea, mock_get_auth_params, mock_execute):
    """close_command should lookup auth and pass an api_call that closes the issue."""
    ctx = make_ctx()

    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.edit_issue.return_value = ({"id": 1}, {"meta": True})
    mock_gitea.return_value.__enter__.return_value = client

    close_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        issue_id=3,
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_get_auth_params.assert_called_once_with(
        config_path="/tmp/config", account_name="acct", token=None, base_url=None
    )
    mock_execute.assert_called_once()

    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli issue close"

    # Execute the passed api_call to ensure delegation
    result = call_kwargs["api_call"]()
    assert result == ({"id": 1}, {"meta": True})

    client.issue.edit_issue.assert_called_once_with(
        owner="owner",
        repository="repo",
        index=3,
        state="closed",
    )


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_close_command_accepts_the_deprecated_index(mock_gitea, mock_get_auth_params, mock_execute):
    """`--index` should name the same issue as `--issue-id`, so old scripts keep working."""
    ctx = make_ctx()

    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.edit_issue.return_value = ({"id": 1}, {"meta": True})
    mock_gitea.return_value.__enter__.return_value = client

    close_command(ctx=ctx, owner="owner", repository="repo", index=5)

    call_kwargs = mock_execute.call_args[1]
    call_kwargs["api_call"]()

    client.issue.edit_issue.assert_called_once_with(
        owner="owner",
        repository="repo",
        index=5,
        state="closed",
    )


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_close_command_posts_the_comment_after_closing(mock_gitea, mock_get_auth_params, mock_execute):
    """`--comment` should close the issue and then comment on it, in that order."""
    ctx = make_ctx()

    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.edit_issue.return_value = ({"id": 1}, {"meta": True})
    client.comment.create_comment.return_value = ({"id": 9}, {"status_code": 201})
    mock_gitea.return_value.__enter__.return_value = client

    close_command(ctx=ctx, owner="owner", repository="repo", issue_id=3, comment="Fixed.")

    call_kwargs = mock_execute.call_args[1]
    result = call_kwargs["api_call"]()

    client.issue.edit_issue.assert_called_once_with(
        owner="owner",
        repository="repo",
        index=3,
        state="closed",
    )
    client.comment.create_comment.assert_called_once_with(
        owner="owner",
        repository="repo",
        index=3,
        body="Fixed.",
    )

    # The issue is closed before the comment is posted, so a comment that cannot
    # be posted leaves the issue closed rather than the close undone. Both calls
    # are recorded on the same client, so their order is readable from it.
    assert [call[0] for call in client.mock_calls if call[0] in {"issue.edit_issue", "comment.create_comment"}] == [
        "issue.edit_issue",
        "comment.create_comment",
    ]

    # The result is the closed issue: the comment is what the command does on
    # the way past, not what it was asked for.
    assert result == ({"id": 1}, {"meta": True})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_close_command_without_a_comment_posts_none(mock_gitea, mock_get_auth_params, mock_execute):
    """Omitting `--comment` should close the issue and say nothing on it."""
    ctx = make_ctx()

    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.edit_issue.return_value = ({"id": 1}, {"meta": True})
    mock_gitea.return_value.__enter__.return_value = client

    close_command(ctx=ctx, owner="owner", repository="repo", issue_id=3, comment=None)

    call_kwargs = mock_execute.call_args[1]
    call_kwargs["api_call"]()

    client.issue.edit_issue.assert_called_once()
    client.comment.create_comment.assert_not_called()


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_close_command_needs_a_repository(mock_gitea, mock_get_auth_params, mock_execute):
    """Omitting `--repository` should be reported as the error naming what to pass.

    The check runs inside `api_call`, so the message reaches the user through
    the same handling as every other command's rather than as a traceback.
    """
    from gitea.cli.utils.errors import CommandError

    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")
    mock_gitea.return_value.__enter__.return_value = MagicMock()

    close_command(ctx=ctx, owner="owner", issue_id=3)

    api_call = mock_execute.call_args[1]["api_call"]

    with pytest.raises(CommandError, match=r"'gitea-cli issue close' needs a repository: pass --repository"):
        api_call()


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_close_command_needs_an_issue(mock_gitea, mock_get_auth_params, mock_execute):
    """Naming no issue should point at `--issue-id` rather than at `--index`."""
    from gitea.cli.utils.errors import CommandError

    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")
    mock_gitea.return_value.__enter__.return_value = MagicMock()

    close_command(ctx=ctx, owner="owner", repository="repo")

    api_call = mock_execute.call_args[1]["api_call"]

    with pytest.raises(CommandError, match=r"'gitea-cli issue close' needs an issue: pass --issue-id NUMBER"):
        api_call()
