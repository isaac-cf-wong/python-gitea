"""Unit tests for the notification CLI commands."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import typer

from gitea.cli.notification.list import list_command
from gitea.cli.notification.read import read_command


def make_ctx():
    """Create a mock context object."""
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_list_command_user_notifications(mock_gitea, mock_get_auth_params, mock_execute):
    """list_command without owner/repo should list the user's notifications."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.notification.list_notifications.return_value = ([{"id": 1}], {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    list_command(
        ctx=ctx,
        owner=None,
        repository=None,
        all_notifications=True,
        status_types=["unread"],
        subject_type=None,
        since=None,
        before=None,
        page=1,
        limit=10,
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli notification list"

    result = call_kwargs["api_call"]()
    client.notification.list_notifications.assert_called_once_with(
        all_notifications=True,
        status_types=["unread"],
        subject_type=None,
        since=None,
        before=None,
        page=1,
        limit=10,
    )
    assert result == ([{"id": 1}], {"status_code": 200})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_list_command_repo_notifications(mock_gitea, mock_get_auth_params, mock_execute):
    """list_command with owner/repo should list repo notifications."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.notification.list_repo_notifications.return_value = ([{"id": 2}], {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    list_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        all_notifications=None,
        status_types=None,
        subject_type=None,
        since=None,
        before=None,
        page=None,
        limit=None,
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    result = call_kwargs["api_call"]()
    client.notification.list_repo_notifications.assert_called_once_with(
        owner="owner",
        repository="repo",
        all_notifications=None,
        status_types=None,
        subject_type=None,
        since=None,
        before=None,
        page=None,
        limit=None,
    )
    assert result == ([{"id": 2}], {"status_code": 200})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_read_command_user_notifications(mock_gitea, mock_get_auth_params, mock_execute):
    """read_command without owner/repo should mark user notifications read."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.notification.read_notifications.return_value = ([{"id": 1}], {"status_code": 205})
    mock_gitea.return_value.__enter__.return_value = client

    read_command(
        ctx=ctx,
        owner=None,
        repository=None,
        last_read_at=None,
        all_notifications=True,
        status_types=None,
        to_status="read",
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli notification read"

    result = call_kwargs["api_call"]()
    client.notification.read_notifications.assert_called_once_with(
        last_read_at=None,
        all_notifications=True,
        status_types=None,
        to_status="read",
    )
    assert result == ([{"id": 1}], {"status_code": 205})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_read_command_repo_notifications(mock_gitea, mock_get_auth_params, mock_execute):
    """read_command with owner/repo should mark repo notifications read."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.notification.read_repo_notifications.return_value = ([{"id": 2}], {"status_code": 205})
    mock_gitea.return_value.__enter__.return_value = client

    read_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        last_read_at=None,
        all_notifications=True,
        status_types=None,
        to_status=None,
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    result = call_kwargs["api_call"]()
    client.notification.read_repo_notifications.assert_called_once_with(
        owner="owner",
        repository="repo",
        last_read_at=None,
        all_notifications=True,
        status_types=None,
        to_status=None,
    )
    assert result == ([{"id": 2}], {"status_code": 205})


@pytest.mark.parametrize(
    ("owner", "repository"),
    [
        ("owner", None),
        (None, "repo"),
    ],
)
@patch("gitea.cli.utils.auth.get_auth_params")
def test_list_command_rejects_partial_selector(mock_get_auth_params, owner, repository):
    """list_command should reject owner-only or repository-only selectors."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    with pytest.raises(typer.BadParameter):
        list_command(
            ctx=ctx,
            owner=owner,
            repository=repository,
            all_notifications=None,
            status_types=None,
            subject_type=None,
            since=None,
            before=None,
            page=None,
            limit=None,
            account_name="acct",
            token=None,
            base_url=None,
        )


@pytest.mark.parametrize(
    ("owner", "repository"),
    [
        ("owner", None),
        (None, "repo"),
    ],
)
@patch("gitea.cli.utils.auth.get_auth_params")
def test_read_command_rejects_partial_selector(mock_get_auth_params, owner, repository):
    """read_command should reject owner-only or repository-only selectors."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    with pytest.raises(typer.BadParameter):
        read_command(
            ctx=ctx,
            owner=owner,
            repository=repository,
            last_read_at=None,
            all_notifications=None,
            status_types=None,
            to_status=None,
            account_name="acct",
            token=None,
            base_url=None,
        )
