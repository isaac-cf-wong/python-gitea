"""Unit tests for comment CLI main registration."""

from gitea.cli.comment import main as comment_main


def test_register_commands_attached():
    """The comment_app should have the add/list/edit/delete commands registered."""
    names = [cmd.name for cmd in comment_main.comment_app.registered_commands]
    assert "add" in names
    assert "list" in names
    assert "edit" in names
    assert "delete" in names
