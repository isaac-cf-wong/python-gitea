"""Unit tests for the commands that act on an Actions workflow run.

Cancelling and rerunning each have two endpoints behind one client method,
selected by a flag. So what these tests are mostly about is that the flag arrives:
a command that dropped `force` would ask politely and report success, leaving the
stuck run exactly as it was, and one that dropped `failed_jobs_only` would rerun
a whole matrix instead of the one job that failed. Neither is visible in the
envelope.
"""

from __future__ import annotations

import pytest

from gitea.cli.actions.run.approve import approve_run_command
from gitea.cli.actions.run.cancel import cancel_run_command
from gitea.cli.actions.run.delete import delete_run_command
from gitea.cli.actions.run.force_cancel import force_cancel_run_command
from gitea.cli.actions.run.rerun import rerun_run_command
from gitea.cli.utils.errors import CommandError
from tests.cli.actions.invoking import api_call_of, invoke

OWNER = "owner"
REPOSITORY = "repo"
RUN_ID = 42
JOB_ID = 118

OF_RUN = {"owner": OWNER, "repository": REPOSITORY, "run_id": RUN_ID}
CREDENTIALS = {"account_name": "acct", "token": None, "base_url": None}


@pytest.mark.parametrize(
    ("command", "arguments", "method", "expected", "command_name"),
    [
        (
            cancel_run_command,
            {},
            "cancel_workflow_run",
            {**OF_RUN, "force": False},
            "gitea-cli actions run cancel",
        ),
        (
            force_cancel_run_command,
            {},
            "cancel_workflow_run",
            {**OF_RUN, "force": True},
            "gitea-cli actions run force-cancel",
        ),
        (
            approve_run_command,
            {},
            "approve_workflow_run",
            OF_RUN,
            "gitea-cli actions run approve",
        ),
        (
            rerun_run_command,
            {"failed_jobs": False},
            "rerun_workflow_run",
            {**OF_RUN, "failed_jobs_only": False},
            "gitea-cli actions run rerun",
        ),
        (
            rerun_run_command,
            {"failed_jobs": True},
            "rerun_workflow_run",
            {**OF_RUN, "failed_jobs_only": True},
            "gitea-cli actions run rerun",
        ),
        (
            delete_run_command,
            {},
            "delete_workflow_run",
            OF_RUN,
            "gitea-cli actions run delete",
        ),
    ],
    ids=["cancel", "force-cancel", "approve", "rerun", "rerun-failed-jobs", "delete"],
)
def test_each_command_addresses_the_run_it_was_given(
    command: object, arguments: dict, method: str, expected: dict, command_name: str
) -> None:
    """Each command should call its method with the run named, and the flag it implies."""
    invocation = invoke(
        command,
        {"owner": OWNER, "repository": REPOSITORY, "run_id": RUN_ID, **arguments, **CREDENTIALS},
        method=method,
    )

    assert invocation.command_name == command_name
    getattr(invocation.client.actions, method).assert_called_once_with(**expected)


@pytest.mark.parametrize(
    ("command", "arguments", "method"),
    [
        (cancel_run_command, {}, "cancel_workflow_run"),
        (force_cancel_run_command, {}, "cancel_workflow_run"),
        (approve_run_command, {}, "approve_workflow_run"),
        (rerun_run_command, {"failed_jobs": False}, "rerun_workflow_run"),
        (delete_run_command, {}, "delete_workflow_run"),
    ],
    ids=["cancel", "force-cancel", "approve", "rerun", "delete"],
)
def test_each_command_needs_a_repository(command: object, arguments: dict, method: str) -> None:
    """A run belongs to a repository, so omitting one should be reported and not guessed.

    `--repository` is optional at the parser level everywhere in this CLI, which
    is what lets the commands that do have an owner-wide form accept it being
    left out. These have none, so the omission has to be caught here - and a
    command that let it through would build a URL with an empty path segment.
    """
    api_call = api_call_of(
        command,
        {"owner": OWNER, "repository": None, "run_id": RUN_ID, **arguments, **CREDENTIALS},
        method=method,
    )

    with pytest.raises(CommandError, match="needs a repository"):
        api_call()


def test_rerunning_one_job_names_both_the_run_and_the_job() -> None:
    """The job rerun is addressed through its run, so both IDs should be forwarded.

    Reading a job takes `--job-id` alone, because Gitea addresses a job directly;
    this endpoint sits under the run. A command forwarding only the job would
    address a path that does not exist.
    """
    from gitea.cli.actions.job.rerun import rerun_job_command

    invocation = invoke(
        rerun_job_command,
        {
            "owner": OWNER,
            "repository": REPOSITORY,
            "run_id": RUN_ID,
            "job_id": JOB_ID,
            **CREDENTIALS,
        },
        method="rerun_workflow_job",
    )

    assert invocation.command_name == "gitea-cli actions job rerun"
    invocation.client.actions.rerun_workflow_job.assert_called_once_with(
        owner=OWNER, repository=REPOSITORY, run_id=RUN_ID, job_id=JOB_ID
    )
