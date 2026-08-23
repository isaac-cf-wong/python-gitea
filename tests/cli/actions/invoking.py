"""Running one Actions command with the client replaced, for the tests below.

Every command in this family does the same three things - resolve the
credentials, build the client, forward the options - so a test that wants to know
which options were forwarded has the same setup to write each time. It is written
once here.

The client is a `MagicMock` rather than a recording HTTP session on purpose: what
these tests are about is the arguments the command passes, one layer above the
request. That the arguments then become the right URL is
`tests/actions/test_actions_requests.py`, and that the whole thing emits the right
envelope is `tests/cli/test_cli_contract.py`; between the three, a value dropped
anywhere on the way has a test that sees it.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

CONFIG_PATH = "/tmp/config"
TOKEN = "tok"
BASE_URL = "https://gitea.example.com"

# What the fake client answers with, in the shape a command's caller expects: the
# payload and the metadata. The payload itself is not what these tests assert on.
ANSWER: tuple[dict[str, Any], dict[str, Any]] = ({}, {"status_code": 200})


def make_ctx() -> SimpleNamespace:
    """Create a context carrying the configuration path a command reads.

    Returns:
        The stand-in context.

    """
    return SimpleNamespace(obj={"config_path": CONFIG_PATH})


@dataclass
class Invocation:
    """What one command did when it ran.

    Attributes:
        client: The client it called, so the arguments it forwarded can be read
            off it.
        command_name: The name it reported itself by, which is what its error
            messages name it as.
        returned: What its API call handed back.

    """

    client: MagicMock
    command_name: str
    returned: Any


def invoke(
    command: Any,
    arguments: dict[str, Any],
    *,
    method: str,
    answer: Any = None,
    helper: str = "execute_api_command",
) -> Invocation:
    """Run one command, with the client and the credentials replaced.

    Args:
        command: The command function to run.
        arguments: The options to run it with, `ctx` excluded.
        method: The `client.actions` method the command is expected to call.
        answer: What that method answers with. Defaults to an empty payload with
            a successful status.
        helper: The helper the command routes its result through -
            `execute_api_command` for one that only reports an API result, or
            `execute_api_call` for one with a rendering of its own.

    Returns:
        What the command did.

    """
    with (
        patch(f"gitea.cli.utils.api.{helper}") as mock_execute,
        patch("gitea.cli.utils.auth.get_auth_params") as mock_get_auth_params,
        patch("gitea.client.gitea.Gitea") as mock_gitea,
    ):
        mock_get_auth_params.return_value = (TOKEN, BASE_URL)
        client = MagicMock()
        getattr(client.actions, method).return_value = ANSWER if answer is None else answer
        mock_gitea.return_value.__enter__.return_value = client

        command(ctx=make_ctx(), **arguments)

        keywords = mock_execute.call_args[1]
        returned = keywords["api_call"]()

    return Invocation(client=client, command_name=keywords["command_name"], returned=returned)


def api_call_of(
    command: Any,
    arguments: dict[str, Any],
    *,
    method: str,
    answer: Any = None,
    refusal: BaseException | None = None,
    helper: str = "execute_api_command",
) -> Any:
    """Run one command and hand back its API call unexecuted, for a test of a refusal.

    A command that refuses an invocation raises from inside the callable
    `execute_api_command` was handed, not from the command itself - that is what
    makes the message reach the user rather than a traceback - so a test of a
    refusal needs the callable rather than the result of calling it.

    Args:
        command: The command function to run.
        arguments: The options to run it with, `ctx` excluded.
        method: The `client.actions` method the command would call.
        answer: What that method answers with.
        refusal: What that method raises instead of answering, for a test of a
            refusal the client makes rather than the command. The rule about
            which scopes an endpoint has lives in the client, so a command's
            share of it is the conversion of that refusal and nothing else -
            which is what standing the refusal in here tests.
        helper: The helper the command routes its result through.

    Returns:
        The callable, ready to be called inside `pytest.raises`.

    """
    with (
        patch(f"gitea.cli.utils.api.{helper}") as mock_execute,
        patch("gitea.cli.utils.auth.get_auth_params") as mock_get_auth_params,
        patch("gitea.client.gitea.Gitea") as mock_gitea,
    ):
        mock_get_auth_params.return_value = (TOKEN, BASE_URL)
        client = MagicMock()
        if refusal is None:
            getattr(client.actions, method).return_value = ANSWER if answer is None else answer
        else:
            getattr(client.actions, method).side_effect = refusal
        mock_gitea.return_value.__enter__.return_value = client

        command(ctx=make_ctx(), **arguments)

        return mock_execute.call_args[1]["api_call"]
