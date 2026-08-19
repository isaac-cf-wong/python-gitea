"""Unit tests for repository CLI main registration."""

from gitea.cli.repository import main as repository_main
from gitea.cli.repository.list import list_command


def test_register_commands_attached():
    """The repository_app should have the list command registered."""
    names = [cmd.name for cmd in repository_main.repository_app.registered_commands]
    assert "list" in names


def test_the_registered_command_is_the_one_that_lists_repositories():
    """The registration should name the command, its callback and its help text.

    Asserting only that a command called `list` exists passes a registration that
    wired the wrong callable, or none, or lost the help text that `--help` prints:
    the app records whatever it is handed.
    """
    (command,) = repository_main.repository_app.registered_commands

    assert command.name == "list"
    assert command.callback is list_command
    assert command.help == "List repositories of an owner."
