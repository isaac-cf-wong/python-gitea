"""Unit tests for label CLI main registration."""

from gitea.cli.label import main as label_main


def test_register_commands_attached():
    """The label_app should have the create/list/update/delete commands registered."""
    names = [cmd.name for cmd in label_main.label_app.registered_commands]
    assert "create" in names
    assert "list" in names
    assert "update" in names
    assert "delete" in names
