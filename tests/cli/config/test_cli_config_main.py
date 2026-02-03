"""Tests for the config CLI main module."""

from __future__ import annotations

from typer.testing import CliRunner

from gitea.cli.config.main import config_app

runner = CliRunner()


class TestConfigApp:
    """Tests for the config app."""

    def test_config_help(self) -> None:
        """Test that config help works."""
        result = runner.invoke(config_app, ["--help"])
        assert result.exit_code == 0
        assert "config" in result.stdout.lower()

    def test_config_add_command_exists(self) -> None:
        """Test that add command is available."""
        result = runner.invoke(config_app, ["add", "--help"])
        assert result.exit_code == 0

    def test_config_delete_command_exists(self) -> None:
        """Test that delete command is available."""
        result = runner.invoke(config_app, ["delete", "--help"])
        assert result.exit_code == 0

    def test_config_list_command_exists(self) -> None:
        """Test that list command is available."""
        result = runner.invoke(config_app, ["list", "--help"])
        assert result.exit_code == 0

    def test_config_update_command_exists(self) -> None:
        """Test that update command is available."""
        result = runner.invoke(config_app, ["update", "--help"])
        assert result.exit_code == 0
