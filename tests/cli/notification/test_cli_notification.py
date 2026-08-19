"""Unit tests for the notification CLI commands."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from gitea.cli.main import app
from gitea.cli.notification.list import list_command
from gitea.cli.notification.read import read_command
from tests.cli.rendering import unrendered
from tests.transport import RecordingSession

runner = CliRunner()

# Credentials passed on the command line, so that the invocation authenticates
# without reading a configuration file - and cannot read the developer's own.
_BASE_URL = "https://gitea.example.com"


def make_ctx():
    """Create a mock context object."""
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


def _invocation(tmp_path: Path, *arguments: str) -> list[str]:
    """Build the argument list of a `notification` invocation.

    Args:
        tmp_path: Directory to point `--config-path` at, so that no
            configuration of the machine running the tests is read.
        *arguments: Arguments of the command under test.

    Returns:
        The full argument list to hand to the runner.

    """
    return [
        "--config-path",
        str(tmp_path / "config.yaml"),
        "notification",
        *arguments,
        "--token",
        "tok",
        "--base-url",
        _BASE_URL,
    ]


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


class TestNotificationScopeThroughTheCli:
    """How the `--owner`/`--repository` pair of the `notification` family reads on the command line.

    The tests above call the command functions directly, which leaves the options
    themselves untested: a scope wired to the wrong parameter, or a rejection
    Typer never turns into a usage error, would pass them. These run the
    invocations the user types and assert the URL each one reached, recorded at
    the session the client makes its requests through.
    """

    def test_no_scope_lists_the_authenticated_users_notifications(self, tmp_path: Path) -> None:
        """Given neither option, `notification list` should ask for the user's own notifications."""
        session = RecordingSession()

        with patch("gitea.client.gitea.requests.Session", return_value=session):
            result = runner.invoke(app, _invocation(tmp_path, "list"))

        assert result.exit_code == 0, result.output
        assert session.urls == [f"{_BASE_URL}/api/v1/notifications"]

    def test_a_full_scope_lists_the_notifications_of_that_repository(self, tmp_path: Path) -> None:
        """Given both options, `notification list` should ask for that repository's notifications."""
        session = RecordingSession()

        with patch("gitea.client.gitea.requests.Session", return_value=session):
            result = runner.invoke(
                app,
                _invocation(tmp_path, "list", "--owner", "owner", "--repository", "repo"),
            )

        assert result.exit_code == 0, result.output
        assert session.urls == [f"{_BASE_URL}/api/v1/repos/owner/repo/notifications"]

    @pytest.mark.parametrize("command", ["list", "read"])
    @pytest.mark.parametrize("half", [["--owner", "owner"], ["--repository", "repo"]])
    def test_half_a_scope_is_refused_before_any_request(self, tmp_path: Path, command: str, half: list[str]) -> None:
        """Either option alone should be refused with a message naming both, and no call made."""
        session = RecordingSession()

        with patch("gitea.client.gitea.requests.Session", return_value=session):
            result = runner.invoke(app, _invocation(tmp_path, command, *half))

        # A usage error, so that a script can tell it from the failure of a call.
        assert result.exit_code == 2
        assert result.stdout == ""
        # The message is asserted by the words it is made of: the layout Rich
        # gives a usage error depends on the terminal running the tests.
        message = unrendered(result.stderr)
        assert "--owner" in message
        assert "--repository" in message
        assert "together" in message
        assert session.requests == []
