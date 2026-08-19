"""Unit tests for the `org list` command.

Two things are worth pinning separately. That the command hands the client what
it was asked for, which the delegation tests below assert, and *which endpoint*
that reaches: an organization listing is read from `/user/orgs` for the account
holding the token and from `/users/{username}/orgs` for a named one, and a
command that mixed the two would answer with somebody else's organizations while
looking like it worked. The URL is therefore asserted through the session the
real client builds its requests for.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from gitea.cli.main import app
from gitea.cli.organization.list import list_command
from tests.cli.envelope import parse_envelope
from tests.transport import RecordingSession

runner = CliRunner()

BASE_URL = "https://gitea.invalid"
ORGANIZATION = {"id": 23, "username": "my-org", "full_name": "My Org", "visibility": "limited"}


def make_ctx():
    """Create a mock Typer context with config_path.

    Returns:
        A stand-in context carrying the configuration path.

    """
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


def run(*arguments: str) -> tuple[object, RecordingSession]:
    """Run `org list` against a session recording what it asked for.

    Args:
        *arguments: Options to pass after the command.

    Returns:
        The result of the invocation, and the recording session.

    """
    session = RecordingSession(payload=[ORGANIZATION])
    with patch("gitea.client.gitea.requests.Session", return_value=session):
        result = runner.invoke(
            app,
            ["--output", "json", "org", "list", "--token", "tok", "--base-url", BASE_URL, *arguments],
        )
    return result, session


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_list_command_calls_execute_and_delegates(mock_gitea, mock_get_auth_params, mock_execute):
    """list_command should look up auth and pass an api_call that calls list_organizations."""
    ctx = make_ctx()

    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.organization.list_organizations.return_value = ([ORGANIZATION], {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    list_command(
        ctx=ctx,
        username="alice",
        page=3,
        limit=15,
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_get_auth_params.assert_called_once_with(
        config_path="/tmp/config", account_name="acct", token=None, base_url=None
    )
    mock_execute.assert_called_once()

    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli org list"

    result = call_kwargs["api_call"]()
    assert result == ([ORGANIZATION], {"status_code": 200})

    client.organization.list_organizations.assert_called_once_with(username="alice", page=3, limit=15)


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_list_command_defaults_to_the_authenticated_account(mock_gitea, mock_get_auth_params, mock_execute):
    """Omitting `--username` should ask for the organizations of the token's own account."""
    mock_get_auth_params.return_value = ("tok", BASE_URL)

    client = MagicMock()
    client.organization.list_organizations.return_value = ([ORGANIZATION], {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    list_command(ctx=make_ctx(), username=None, page=None, limit=None, account_name=None, token=None, base_url=None)

    mock_execute.call_args[1]["api_call"]()

    client.organization.list_organizations.assert_called_once_with(username=None, page=None, limit=None)


def test_the_authenticated_listing_reaches_the_user_endpoint():
    """`org list` should read the token's own organizations from `/user/orgs`."""
    result, session = run()

    assert result.exit_code == 0, result.output
    assert parse_envelope(result.stdout)["data"] == [ORGANIZATION]
    assert session.requests == [("GET", f"{BASE_URL}/api/v1/user/orgs")]


def test_a_named_account_reaches_that_accounts_endpoint():
    """`--username` should read that account's organizations rather than the token's."""
    result, session = run("--username", "alice")

    assert result.exit_code == 0, result.output
    assert session.requests == [("GET", f"{BASE_URL}/api/v1/users/alice/orgs")]


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        ((), {}),
        (("--page", "2"), {"page": 2}),
        (("--limit", "5"), {"limit": 5}),
        (("--page", "2", "--limit", "5"), {"page": 2, "limit": 5}),
    ],
)
def test_pagination_options_reach_the_request(arguments: tuple[str, ...], expected: dict[str, int]):
    """`--page` and `--limit` should be sent to the endpoint, and only when passed."""
    result, session = run(*arguments)

    assert result.exit_code == 0, result.output
    assert session.params == [expected]
