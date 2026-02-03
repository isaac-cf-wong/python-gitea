"""Unit tests for issue CLI main registration."""

from gitea.cli.issue import main as issue_main


def test_register_commands_attached():
    """The issue_app should have the edit/get/list commands registered."""
    # Typer stores registered commands on the attribute 'registered_commands'
    names = [cmd.name for cmd in issue_main.issue_app.registered_commands]
    assert "edit" in names
    assert "get" in names
    assert "list" in names
