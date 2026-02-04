"""Unit tests for pull-request CLI main registration."""

from gitea.cli.pull_request import main as pr_main


def test_register_commands_attached():
    """The pull_request_app should have the list command registered."""
    names = [cmd.name for cmd in pr_main.pull_request_app.registered_commands]
    assert "list" in names
