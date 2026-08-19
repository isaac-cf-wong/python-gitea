"""Unit tests for the `repo list` command.

The endpoint is the part of this command that can be wrong while it still looks
right: Gitea serves an organization's repositories at `/orgs/{owner}/repos` and a
user's at `/users/{owner}/repos`, so a command that read `--owner-type` the wrong
way round would ask the wrong endpoint and report an empty listing or a 404 for
an owner that exists. Both readings are therefore asserted through the session
the real client builds its requests for, and not only through the arguments the
command hands the client.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from gitea.cli.main import app
from gitea.cli.repository.list import OwnerType, list_command
from tests.cli.envelope import parse_envelope
from tests.cli.transport import RecordingSession

runner = CliRunner()

BASE_URL = "https://gitea.invalid"
REPOSITORY = {"id": 254, "name": "r", "full_name": "o/r", "private": False}


def make_ctx():
    """Create a mock Typer context with config_path.

    Returns:
        A stand-in context carrying the configuration path.

    """
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


def run(*arguments: str) -> tuple[object, RecordingSession]:
    """Run `repo list` against a session recording what it asked for.

    Args:
        *arguments: Options to pass after the command.

    Returns:
        The result of the invocation, and the recording session.

    """
    session = RecordingSession(payload=[REPOSITORY])
    with patch("gitea.client.gitea.requests.Session", return_value=session):
        result = runner.invoke(
            app,
            ["--output", "json", "repo", "list", "--token", "tok", "--base-url", BASE_URL, *arguments],
        )
    return result, session


def delegate(**overrides) -> MagicMock:
    """Run the command against a stub client and return that client.

    Args:
        **overrides: Options to pass to the command, over the defaults of an
            organization owner without pagination.

    Returns:
        The stub client the command called.

    """
    client = MagicMock()
    client.repository.list_repositories.return_value = ([REPOSITORY], {"status_code": 200})

    arguments = {
        "ctx": make_ctx(),
        "owner": "my-org",
        "owner_type": OwnerType.ORGANIZATION,
        "page": None,
        "limit": None,
        "account_name": None,
        "token": "tok",
        "base_url": BASE_URL,
        **overrides,
    }

    with (
        patch("gitea.cli.utils.api.execute_api_command") as mock_execute,
        patch("gitea.cli.utils.auth.get_auth_params", return_value=("tok", BASE_URL)),
        patch("gitea.client.gitea.Gitea") as mock_gitea,
    ):
        mock_gitea.return_value.__enter__.return_value = client
        list_command(**arguments)

        assert mock_execute.call_args[1]["command_name"] == "gitea-cli repo list"
        assert mock_execute.call_args[1]["api_call"]() == ([REPOSITORY], {"status_code": 200})

    return client


def api_call_of(**overrides):
    """Build the command's api_call without running it.

    Args:
        **overrides: Options to pass to the command, over the defaults of an
            organization owner without pagination.

    Returns:
        The callable the command handed to `execute_api_command`.

    """
    arguments = {
        "ctx": make_ctx(),
        "owner": "my-org",
        "owner_type": OwnerType.ORGANIZATION,
        "page": None,
        "limit": None,
        "account_name": None,
        "token": "tok",
        "base_url": BASE_URL,
        **overrides,
    }

    with (
        patch("gitea.cli.utils.api.execute_api_command") as mock_execute,
        patch("gitea.cli.utils.auth.get_auth_params", return_value=("tok", BASE_URL)),
    ):
        list_command(**arguments)

    return mock_execute.call_args[1]["api_call"]


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_list_command_calls_execute_and_delegates(mock_gitea, mock_get_auth_params, mock_execute):
    """list_command should look up auth and pass an api_call that calls list_repositories."""
    ctx = make_ctx()

    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.repository.list_repositories.return_value = ([REPOSITORY], {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    list_command(
        ctx=ctx,
        owner="my-org",
        owner_type=OwnerType.ORGANIZATION,
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
    assert call_kwargs["command_name"] == "gitea-cli repo list"

    result = call_kwargs["api_call"]()
    assert result == ([REPOSITORY], {"status_code": 200})

    client.repository.list_repositories.assert_called_once_with(
        username=None,
        organization="my-org",
        page=3,
        limit=15,
    )


def test_an_organization_owner_is_passed_as_the_organization():
    """The default owner type should name the owner as an organization, and no user."""
    client = delegate()

    client.repository.list_repositories.assert_called_once_with(
        username=None,
        organization="my-org",
        page=None,
        limit=None,
    )


def test_a_user_owner_is_passed_as_the_username():
    """`--owner-type user` should name the owner as a user, and no organization."""
    client = delegate(owner="alice", owner_type=OwnerType.USER)

    client.repository.list_repositories.assert_called_once_with(
        username="alice",
        organization=None,
        page=None,
        limit=None,
    )


def test_an_organization_owner_reaches_the_organization_endpoint():
    """`repo list --owner o` should read `/orgs/o/repos`."""
    result, session = run("--owner", "o")

    assert result.exit_code == 0, result.output
    assert parse_envelope(result.stdout)["data"] == [REPOSITORY]
    assert session.requests == [("GET", f"{BASE_URL}/api/v1/orgs/o/repos")]


def test_the_organization_owner_type_can_be_named_explicitly():
    """Passing the default owner type should reach the same endpoint as omitting it."""
    result, session = run("--owner", "o", "--owner-type", "organization")

    assert result.exit_code == 0, result.output
    assert session.requests == [("GET", f"{BASE_URL}/api/v1/orgs/o/repos")]


def test_a_user_owner_reaches_the_user_endpoint():
    """`--owner-type user` should read `/users/o/repos` instead."""
    result, session = run("--owner", "o", "--owner-type", "user")

    assert result.exit_code == 0, result.output
    assert parse_envelope(result.stdout)["data"] == [REPOSITORY]
    assert session.requests == [("GET", f"{BASE_URL}/api/v1/users/o/repos")]


def test_an_unknown_owner_type_is_a_usage_error():
    """A third kind of owner should be refused by the parser, naming the two there are."""
    result, session = run("--owner", "o", "--owner-type", "team")

    assert result.exit_code == 2
    assert session.requests == []
    assert "organization" in result.output
    assert "user" in result.output


def test_an_unknown_owner_type_is_never_read_as_an_organization():
    """A kind that is neither should be refused rather than fall back to one of them.

    The parser refuses one that is typed, but the command is also a function a
    caller can hand a value to, and the fallback that would make this harmless -
    "anything that is not a user is an organization" - is exactly what would send
    a request about an owner the caller never named that way.
    """
    with pytest.raises(ValueError, match="team"):
        api_call_of(owner_type="team")()


def test_the_owner_is_required():
    """Omitting `--owner` should be a usage error rather than a listing of somebody's repositories."""
    result, session = run()

    assert result.exit_code == 2
    assert session.requests == []


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
    result, session = run("--owner", "o", *arguments)

    assert result.exit_code == 0, result.output
    assert session.params == [expected]
