"""Unit tests for the `actions job list` command.

The command exists because it is a different endpoint from `actions run jobs`: it
answers with every job of a scope rather than the jobs of one run. So the filters
are what matter - a dropped `--status` turns "what is waiting for a runner" into
"every job there has ever been" - and so does the scope reaching the client as it
was typed.
"""

from __future__ import annotations

import pytest

from gitea.cli.actions.job.list import list_jobs_command
from gitea.cli.utils.errors import CommandError
from tests.cli.actions.invoking import api_call_of, invoke

OWNER = "owner"
REPOSITORY = "repo"

CREDENTIALS = {"account_name": "acct", "token": None, "base_url": None}


def arguments(**overrides: object) -> dict:
    """Build the options the command is run with.

    Args:
        **overrides: Options to pass instead of the defaults below.

    Returns:
        The options, credentials included.

    """
    return {
        "owner": OWNER,
        "repository": REPOSITORY,
        "admin": False,
        "status": "queued",
        "page": 2,
        "limit": 5,
        **CREDENTIALS,
        **overrides,
    }


def test_every_filter_reaches_the_client() -> None:
    """Each option should be forwarded, since a dropped filter answers with the wrong jobs."""
    invocation = invoke(list_jobs_command, arguments(), method="list_workflow_jobs")

    assert invocation.command_name == "gitea-cli actions job list"
    invocation.client.actions.list_workflow_jobs.assert_called_once_with(
        owner=OWNER, repository=REPOSITORY, admin=False, status="queued", page=2, limit=5
    )


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"repository": None}, {"owner": OWNER, "repository": None, "admin": False}),
        ({"owner": None, "repository": None}, {"owner": None, "repository": None, "admin": False}),
        (
            {"owner": None, "repository": None, "admin": True},
            {"owner": None, "repository": None, "admin": True},
        ),
    ],
    ids=["organization", "account", "instance"],
)
def test_each_scope_reaches_the_client_as_it_was_typed(overrides: dict, expected: dict) -> None:
    """The coordinates decide the scope, so the command should not fill any of them in."""
    invocation = invoke(list_jobs_command, arguments(**overrides), method="list_workflow_jobs")
    forwarded = invocation.client.actions.list_workflow_jobs.call_args[1]

    assert {name: forwarded[name] for name in expected} == expected


def test_a_refusal_from_the_client_is_reported_as_a_message() -> None:
    """A scope the coordinates cannot name should be a message, not a traceback."""
    api_call = api_call_of(
        list_jobs_command,
        arguments(repository=REPOSITORY, owner=None),
        method="list_workflow_jobs",
        refusal=ValueError("addressed by its owner as well"),
    )

    with pytest.raises(CommandError, match="addressed by its owner as well"):
        api_call()
