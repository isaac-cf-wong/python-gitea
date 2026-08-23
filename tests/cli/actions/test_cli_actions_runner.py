"""Unit tests for the Actions runner commands.

The one thing here that is not plain forwarding is `--state`. The CLI names the
two states where the API has a boolean `disabled`, so the translation is a place a
mistake would invert the meaning of the command - disabling the runner that was
meant to be brought back. `is_disabled` is tested over its whole domain rather
than at one convenient value.
"""

from __future__ import annotations

import pytest

from gitea.cli.actions.runner.delete import delete_runner_command
from gitea.cli.actions.runner.get import get_runner_command
from gitea.cli.actions.runner.list import list_runners_command
from gitea.cli.actions.runner.registration_token import runner_registration_token_command
from gitea.cli.actions.runner.state import RunnerState, is_disabled
from gitea.cli.actions.runner.update import update_runner_command
from gitea.cli.utils.errors import CommandError
from tests.cli.actions.invoking import api_call_of, invoke

OWNER = "owner"
REPOSITORY = "repo"
RUNNER_ID = 7

OF_SCOPE = {"owner": OWNER, "repository": REPOSITORY, "admin": False}
CREDENTIALS = {"account_name": "acct", "token": None, "base_url": None}


class TestTheStateTranslation:
    """How `--state` becomes the `disabled` field the API takes."""

    @pytest.mark.parametrize(
        ("state", "disabled"),
        [(RunnerState.ENABLED, False), (RunnerState.DISABLED, True), (None, None)],
        ids=["enabled", "disabled", "unasked"],
    )
    def test_every_state_maps_to_the_field(self, state: RunnerState | None, disabled: bool | None) -> None:
        """Each of the three cases should map to its own value, `None` included.

        `None` has to stay `None` rather than becoming `False`: it is the question
        not being asked, and turning it into `False` would filter a listing down
        to the enabled runners while looking like it listed both.
        """
        assert is_disabled(state) is disabled

    def test_the_states_are_the_two_the_api_has(self) -> None:
        """There should be exactly two states, spelled as the help says they are."""
        assert {state.value for state in RunnerState} == {"enabled", "disabled"}


def test_the_listing_forwards_the_scope_and_the_filter() -> None:
    """The scope and the translated state should both reach the client."""
    invocation = invoke(
        list_runners_command,
        {**OF_SCOPE, "state": RunnerState.DISABLED, **CREDENTIALS},
        method="list_runners",
    )

    assert invocation.command_name == "gitea-cli actions runner list"
    invocation.client.actions.list_runners.assert_called_once_with(
        owner=OWNER, repository=REPOSITORY, admin=False, disabled=True
    )


def test_the_listing_without_a_state_asks_about_neither() -> None:
    """No `--state` should leave the filter unasked, which is what lists both."""
    invocation = invoke(
        list_runners_command,
        {**OF_SCOPE, "state": None, **CREDENTIALS},
        method="list_runners",
    )

    assert invocation.client.actions.list_runners.call_args[1]["disabled"] is None


def test_the_instance_scope_is_asked_for_by_the_admin_flag() -> None:
    """`--admin` should be forwarded rather than turned into an owner of some kind."""
    invocation = invoke(
        list_runners_command,
        {"owner": None, "repository": None, "admin": True, "state": None, **CREDENTIALS},
        method="list_runners",
    )

    forwarded = invocation.client.actions.list_runners.call_args[1]
    assert forwarded["admin"] is True
    assert forwarded["owner"] is None


@pytest.mark.parametrize(
    ("command", "method", "command_name"),
    [
        (get_runner_command, "get_runner", "gitea-cli actions runner get"),
        (delete_runner_command, "delete_runner", "gitea-cli actions runner delete"),
    ],
    ids=["get", "delete"],
)
def test_the_single_runner_commands_address_the_runner(command: object, method: str, command_name: str) -> None:
    """Reading and removing should name the runner and the scope it is registered to."""
    invocation = invoke(
        command,
        {"runner_id": RUNNER_ID, **OF_SCOPE, **CREDENTIALS},
        method=method,
    )

    assert invocation.command_name == command_name
    getattr(invocation.client.actions, method).assert_called_once_with(
        runner_id=RUNNER_ID, owner=OWNER, repository=REPOSITORY, admin=False
    )


@pytest.mark.parametrize(
    ("state", "disabled"),
    [(RunnerState.DISABLED, True), (RunnerState.ENABLED, False)],
    ids=["disable", "enable"],
)
def test_an_update_sends_the_state_it_was_asked_for(state: RunnerState, disabled: bool) -> None:
    """Both directions should reach the client, since an inverted flag is the whole risk."""
    invocation = invoke(
        update_runner_command,
        {"runner_id": RUNNER_ID, "state": state, **OF_SCOPE, **CREDENTIALS},
        method="update_runner",
    )

    assert invocation.command_name == "gitea-cli actions runner update"
    invocation.client.actions.update_runner.assert_called_once_with(
        runner_id=RUNNER_ID, disabled=disabled, owner=OWNER, repository=REPOSITORY, admin=False
    )


def test_the_registration_token_is_asked_for_by_scope_alone() -> None:
    """The token belongs to a scope, so the scope is all the command sends."""
    invocation = invoke(
        runner_registration_token_command,
        {**OF_SCOPE, **CREDENTIALS},
        method="create_runner_registration_token",
    )

    assert invocation.command_name == "gitea-cli actions runner registration-token"
    invocation.client.actions.create_runner_registration_token.assert_called_once_with(
        owner=OWNER, repository=REPOSITORY, admin=False
    )


def test_a_refusal_from_the_client_is_reported_as_a_message() -> None:
    """A scope the coordinates cannot name should be a message, not a traceback."""
    api_call = api_call_of(
        list_runners_command,
        {"owner": OWNER, "repository": None, "admin": True, "state": None, **CREDENTIALS},
        method="list_runners",
        refusal=ValueError("the instance-wide Actions endpoints belong to no owner"),
    )

    with pytest.raises(CommandError, match="belong to no owner"):
        api_call()
