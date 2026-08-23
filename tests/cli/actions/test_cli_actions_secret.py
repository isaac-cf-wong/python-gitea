"""Unit tests for the Actions secret commands.

`set` is the one worth reading. It carries a value that should not be on a command
line - a value there is in the shell history and in the process list of the machine
it ran on - so `--data -` reads it from stdin instead, and the handling of that is
what most of these tests are about: one trailing newline stripped, so that `echo`
and `printf` both send what they look like they send, and an empty stdin reported
rather than stored as an empty secret.
"""

from __future__ import annotations

import io

import pytest

from gitea.cli.actions.secret.delete import delete_secret_command
from gitea.cli.actions.secret.list import list_secrets_command
from gitea.cli.actions.secret.set import read_secret_data, set_secret_command
from gitea.cli.utils.errors import CommandError
from tests.cli.actions.invoking import api_call_of, invoke

OWNER = "owner"
REPOSITORY = "repo"
SECRET_NAME = "DEPLOY_TOKEN"

CREDENTIALS = {"account_name": "acct", "token": None, "base_url": None}


def test_every_option_of_the_listing_reaches_the_client() -> None:
    """The scope and the pagination should be forwarded as they were given."""
    invocation = invoke(
        list_secrets_command,
        {"owner": OWNER, "repository": REPOSITORY, "page": 2, "limit": 5, **CREDENTIALS},
        method="list_secrets",
    )

    assert invocation.command_name == "gitea-cli actions secret list"
    invocation.client.actions.list_secrets.assert_called_once_with(owner=OWNER, repository=REPOSITORY, page=2, limit=5)


def test_the_scope_is_forwarded_as_it_was_given() -> None:
    """Omitting the repository should ask for the organization's secrets, not the repository's.

    A command that filled in a repository would list a different set and look like
    it had worked, which is exactly the mistake the scope convention exists to
    make impossible.
    """
    invocation = invoke(
        list_secrets_command,
        {"owner": OWNER, "repository": None, "page": None, "limit": None, **CREDENTIALS},
        method="list_secrets",
    )

    assert invocation.client.actions.list_secrets.call_args[1]["repository"] is None


def test_a_scope_the_endpoint_does_not_have_is_reported() -> None:
    """A refusal from the client should reach the user as a message rather than a traceback.

    There is no listing of the authenticated account's own secrets, so the client
    refuses that scope. The command's job is to convert the refusal, and without
    the conversion the CLI answers a plausible invocation with a stack trace.
    """
    api_call = api_call_of(
        list_secrets_command,
        {"owner": None, "repository": None, "page": None, "limit": None, **CREDENTIALS},
        method="list_secrets",
        refusal=ValueError("Gitea has no Actions endpoint here for the authenticated account"),
    )

    with pytest.raises(CommandError, match="the authenticated account"):
        api_call()


def test_setting_a_secret_forwards_the_value_and_the_description() -> None:
    """Every option should reach the client, the description included when it was given."""
    invocation = invoke(
        set_secret_command,
        {
            "secret_name": SECRET_NAME,
            "data": "hunter2",
            "owner": OWNER,
            "repository": REPOSITORY,
            "description": "for deploys",
            **CREDENTIALS,
        },
        method="create_or_update_secret",
    )

    assert invocation.command_name == "gitea-cli actions secret set"
    invocation.client.actions.create_or_update_secret.assert_called_once_with(
        secret_name=SECRET_NAME,
        data="hunter2",
        owner=OWNER,
        repository=REPOSITORY,
        description="for deploys",
    )


def test_deleting_a_secret_addresses_it_by_name() -> None:
    """A secret is addressed by name, since Gitea gives it no numeric ID."""
    invocation = invoke(
        delete_secret_command,
        {"secret_name": SECRET_NAME, "owner": OWNER, "repository": REPOSITORY, **CREDENTIALS},
        method="delete_secret",
    )

    assert invocation.command_name == "gitea-cli actions secret delete"
    invocation.client.actions.delete_secret.assert_called_once_with(
        secret_name=SECRET_NAME, owner=OWNER, repository=REPOSITORY
    )


class TestReadingTheValue:
    """Where the value of a secret comes from, and what is done to it on the way."""

    def test_a_value_on_the_command_line_is_taken_as_it_is(self) -> None:
        """Anything but the dash is the value itself, whitespace and all."""
        assert read_secret_data("hunter2 ") == "hunter2 "

    def test_a_dash_reads_stdin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The dash asks for the value to come from stdin instead."""
        monkeypatch.setattr("sys.stdin", io.StringIO("hunter2"))

        assert read_secret_data("-") == "hunter2"

    def test_one_trailing_newline_is_stripped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Piping a value in with `echo` should store it without the shell's newline.

        The newline is the shell's, not the value's. Stripping it is what makes
        the obvious way of piping a secret in do the obvious thing - and a
        secret with a stray newline in it fails authentication somewhere far
        from here, with nothing to say why.
        """
        monkeypatch.setattr("sys.stdin", io.StringIO("hunter2\n"))

        assert read_secret_data("-") == "hunter2"

    def test_only_one_newline_is_stripped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A value that really ends in a newline keeps it, given a second one.

        Which is the whole reason for stripping exactly one rather than every
        trailing newline: a value that ends in one is unusual but legal, and
        `strip` would make it unrepresentable.
        """
        monkeypatch.setattr("sys.stdin", io.StringIO("hunter2\n\n"))

        assert read_secret_data("-") == "hunter2\n"

    def test_internal_whitespace_is_untouched(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A multi-line value - a private key, say - arrives as it was piped in."""
        key = "-----BEGIN KEY-----\nabc\ndef\n-----END KEY-----\n"
        monkeypatch.setattr("sys.stdin", io.StringIO(key))

        assert read_secret_data("-") == key.removesuffix("\n")

    def test_an_empty_stdin_is_reported(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Nothing on stdin should be reported rather than stored as an empty secret.

        A command substitution that produced nothing is the usual cause, and
        storing the empty string would replace a working secret with one that
        fails wherever it is used.
        """
        monkeypatch.setattr("sys.stdin", io.StringIO(""))

        with pytest.raises(CommandError, match="stdin was empty"):
            read_secret_data("-")


def test_the_value_read_from_stdin_is_what_reaches_the_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """The stdin path should be wired into the command, not only available beside it."""
    monkeypatch.setattr("sys.stdin", io.StringIO("hunter2\n"))

    invocation = invoke(
        set_secret_command,
        {
            "secret_name": SECRET_NAME,
            "data": "-",
            "owner": OWNER,
            "repository": REPOSITORY,
            "description": None,
            **CREDENTIALS,
        },
        method="create_or_update_secret",
    )

    assert invocation.client.actions.create_or_update_secret.call_args[1]["data"] == "hunter2"
