"""Unit tests for milestone CLI main registration."""

from gitea.cli.milestone import main as milestone_main


def test_register_commands_attached():
    """The milestone_app should have the create/list commands registered."""
    names = [cmd.name for cmd in milestone_main.milestone_app.registered_commands]
    assert "create" in names
    assert "list" in names
