"""Unit tests for the registration of the Actions CLI commands."""

from __future__ import annotations

from gitea.cli.actions import main as actions_main


def test_the_groups_are_attached_to_the_actions_app() -> None:
    """`actions` should carry every group of the family and nothing else."""
    groups = {group.name for group in actions_main.actions_app.registered_groups}

    assert groups == {"workflow", "run", "job", "artifact", "secret", "variable", "runner"}


def test_the_workflow_group_carries_its_commands() -> None:
    """A workflow is listed, read and dispatched."""
    names = {command.name for command in actions_main.workflow_app.registered_commands}

    assert names == {"list", "get", "dispatch"}


def test_the_run_group_carries_its_commands() -> None:
    """A run is listed, read, asked for its jobs, and acted on."""
    names = {command.name for command in actions_main.run_app.registered_commands}

    assert names == {"list", "get", "jobs", "cancel", "force-cancel", "approve", "rerun", "delete"}


def test_the_job_group_carries_its_commands() -> None:
    """A job is listed, read, rerun, and its logs are printed."""
    names = {command.name for command in actions_main.job_app.registered_commands}

    assert names == {"list", "get", "logs", "rerun"}


def test_the_artifact_group_carries_its_commands() -> None:
    """An artifact is listed, read, downloaded and deleted."""
    names = {command.name for command in actions_main.artifact_app.registered_commands}

    assert names == {"list", "get", "download", "delete"}


def test_the_secret_group_carries_its_commands() -> None:
    """A secret is listed, set and deleted.

    There is no `get`: Gitea stores a secret's value write-only, so a command
    reading one back would have no endpoint to call.
    """
    names = {command.name for command in actions_main.secret_app.registered_commands}

    assert names == {"list", "set", "delete"}


def test_the_variable_group_carries_its_commands() -> None:
    """A variable is listed, read, created, updated and deleted.

    Creating and updating are separate because Gitea's endpoints are: a create on
    an existing name is a conflict rather than an overwrite, where setting a
    secret is one call that does both.
    """
    names = {command.name for command in actions_main.variable_app.registered_commands}

    assert names == {"list", "get", "create", "update", "delete"}


def test_the_runner_group_carries_its_commands() -> None:
    """A runner is listed, read, disabled, removed, and a token is taken for a new one."""
    names = {command.name for command in actions_main.runner_app.registered_commands}

    assert names == {"list", "get", "update", "delete", "registration-token"}
