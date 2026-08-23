"""Unit tests for the Actions variable commands.

Two things here are easy to get wrong and invisible when they are. `update` sends
the rename under the API's own name rather than the option's, and it requires a
value even when only the name is changing - so a command that dropped `--value`
would empty the variable it was asked to rename. And `create` and `update` are
different verbs to the same path, which is the whole difference between refusing
to overwrite and overwriting.
"""

from __future__ import annotations

import pytest

from gitea.cli.actions.variable.create import create_variable_command
from gitea.cli.actions.variable.delete import delete_variable_command
from gitea.cli.actions.variable.get import get_variable_command
from gitea.cli.actions.variable.list import list_variables_command
from gitea.cli.actions.variable.update import update_variable_command
from gitea.cli.utils.errors import CommandError
from tests.cli.actions.invoking import api_call_of, invoke

OWNER = "owner"
REPOSITORY = "repo"
VARIABLE_NAME = "ENVIRONMENT"

OF_SCOPE = {"owner": OWNER, "repository": REPOSITORY}
CREDENTIALS = {"account_name": "acct", "token": None, "base_url": None}


def test_every_option_of_the_listing_reaches_the_client() -> None:
    """The scope and the pagination should be forwarded as they were given."""
    invocation = invoke(
        list_variables_command,
        {**OF_SCOPE, "page": 3, "limit": 7, **CREDENTIALS},
        method="list_variables",
    )

    assert invocation.command_name == "gitea-cli actions variable list"
    invocation.client.actions.list_variables.assert_called_once_with(
        owner=OWNER, repository=REPOSITORY, page=3, limit=7
    )


def test_the_account_scope_is_asked_for_by_omitting_both_coordinates() -> None:
    """Unlike the secrets, a variable listing does exist for the authenticated account."""
    invocation = invoke(
        list_variables_command,
        {"owner": None, "repository": None, "page": None, "limit": None, **CREDENTIALS},
        method="list_variables",
    )

    forwarded = invocation.client.actions.list_variables.call_args[1]
    assert forwarded["owner"] is None
    assert forwarded["repository"] is None


def test_reading_a_variable_addresses_it_by_name() -> None:
    """A variable is addressed by name, since Gitea gives it no numeric ID."""
    invocation = invoke(
        get_variable_command,
        {"variable_name": VARIABLE_NAME, **OF_SCOPE, **CREDENTIALS},
        method="get_variable",
    )

    assert invocation.command_name == "gitea-cli actions variable get"
    invocation.client.actions.get_variable.assert_called_once_with(
        variable_name=VARIABLE_NAME, owner=OWNER, repository=REPOSITORY
    )


def test_creating_a_variable_forwards_the_value_and_the_description() -> None:
    """Creating should pass everything it was given, and nothing it was not."""
    invocation = invoke(
        create_variable_command,
        {
            "variable_name": VARIABLE_NAME,
            "value": "staging",
            **OF_SCOPE,
            "description": "the target",
            **CREDENTIALS,
        },
        method="create_variable",
    )

    assert invocation.command_name == "gitea-cli actions variable create"
    invocation.client.actions.create_variable.assert_called_once_with(
        variable_name=VARIABLE_NAME,
        value="staging",
        owner=OWNER,
        repository=REPOSITORY,
        description="the target",
    )


def test_updating_a_variable_forwards_the_rename_separately_from_the_name() -> None:
    """The variable addressed and the name it is renamed to are two different values.

    Confusing them would either rename nothing or address the variable that does
    not exist yet, and both look like a command that ran.
    """
    invocation = invoke(
        update_variable_command,
        {
            "variable_name": VARIABLE_NAME,
            "value": "production",
            **OF_SCOPE,
            "new_name": "TARGET",
            "description": "renamed",
            **CREDENTIALS,
        },
        method="update_variable",
    )

    assert invocation.command_name == "gitea-cli actions variable update"
    invocation.client.actions.update_variable.assert_called_once_with(
        variable_name=VARIABLE_NAME,
        value="production",
        owner=OWNER,
        repository=REPOSITORY,
        new_name="TARGET",
        description="renamed",
    )


def test_an_update_without_a_rename_leaves_the_name_alone() -> None:
    """Omitting the rename should forward None, so no `name` field is sent at all."""
    invocation = invoke(
        update_variable_command,
        {
            "variable_name": VARIABLE_NAME,
            "value": "production",
            **OF_SCOPE,
            "new_name": None,
            "description": None,
            **CREDENTIALS,
        },
        method="update_variable",
    )

    assert invocation.client.actions.update_variable.call_args[1]["new_name"] is None


def test_deleting_a_variable_addresses_it_by_name() -> None:
    """Deleting should name the variable and the scope it belongs to."""
    invocation = invoke(
        delete_variable_command,
        {"variable_name": VARIABLE_NAME, **OF_SCOPE, **CREDENTIALS},
        method="delete_variable",
    )

    assert invocation.command_name == "gitea-cli actions variable delete"
    invocation.client.actions.delete_variable.assert_called_once_with(
        variable_name=VARIABLE_NAME, owner=OWNER, repository=REPOSITORY
    )


def test_a_refusal_from_the_client_is_reported_as_a_message() -> None:
    """Every command in the family should convert a refusal rather than raise it.

    The rule about which scopes exist lives in the client, so this is the
    command's whole share of it - and a command that skipped the conversion
    answers a mistyped scope with a stack trace.
    """
    api_call = api_call_of(
        get_variable_command,
        {"variable_name": VARIABLE_NAME, "owner": None, "repository": "repo", **CREDENTIALS},
        method="get_variable",
        refusal=ValueError("addressed by its owner as well"),
    )

    with pytest.raises(CommandError, match="addressed by its owner as well"):
        api_call()
