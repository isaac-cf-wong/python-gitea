"""Unit tests for the registration of the Actions CLI commands."""

from __future__ import annotations

from gitea.cli.actions import main as actions_main


def test_the_groups_are_attached_to_the_actions_app() -> None:
    """`actions` should carry the workflow, run and job groups and nothing else."""
    groups = {group.name for group in actions_main.actions_app.registered_groups}

    assert groups == {"workflow", "run", "job"}


def test_the_workflow_group_carries_its_commands() -> None:
    """A workflow is listed, read and dispatched."""
    names = {command.name for command in actions_main.workflow_app.registered_commands}

    assert names == {"list", "get", "dispatch"}


def test_the_run_group_carries_its_commands() -> None:
    """A run is listed, read, and asked for its jobs."""
    names = {command.name for command in actions_main.run_app.registered_commands}

    assert names == {"list", "get", "jobs"}


def test_the_job_group_carries_its_commands() -> None:
    """A job is read and its logs are printed."""
    names = {command.name for command in actions_main.job_app.registered_commands}

    assert names == {"get", "logs"}
