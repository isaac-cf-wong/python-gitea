"""Tests for the config delete CLI command."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from gitea.cli.main import app

runner = CliRunner()


@pytest.fixture
def temp_config_file() -> Path:
    """Create a temporary config file for testing.

    Returns:
        Path to the temporary config file.

    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def temp_config_with_accounts(temp_config_file: Path) -> Path:
    """Create a temporary config file with sample accounts.

    Args:
        temp_config_file: Temporary config file path.

    Returns:
        Path to the temporary config file.

    """
    config = {
        "accounts": {
            "account1": {"name": "account1", "token": "token1", "base_url": "https://gitea.com"},
            "account2": {"name": "account2", "token": "token2", "base_url": "https://gitea.enterprise.com"},
        },
        "default_account": "account1",
    }

    with temp_config_file.open("w") as f:
        yaml.safe_dump(config, f)

    return temp_config_file


class TestDeleteCommand:
    """Tests for the delete config command."""

    def test_delete_command_help(self) -> None:
        """Test delete command help."""
        result = runner.invoke(app, ["config", "delete", "--help"])
        assert result.exit_code == 0

    def test_delete_account_with_force(self, temp_config_with_accounts: Path) -> None:
        """Test deleting an account with force flag."""
        result = runner.invoke(
            app, ["--config-path", str(temp_config_with_accounts), "config", "delete", "--name", "account2", "--force"]
        )

        assert result.exit_code == 0
        assert "deleted successfully" in result.stderr.lower()

        with temp_config_with_accounts.open("r") as f:
            config = yaml.safe_load(f)
        assert "account2" not in config["accounts"]

    def test_delete_account_cancel_confirmation(self, temp_config_with_accounts: Path) -> None:
        """Test canceling account deletion."""
        result = runner.invoke(
            app,
            ["--config-path", str(temp_config_with_accounts), "config", "delete", "--name", "account2"],
            input="n\n",
        )

        assert "deletion cancelled" in result.stdout.lower()

        with temp_config_with_accounts.open("r") as f:
            config = yaml.safe_load(f)
        assert "account2" in config["accounts"]

    def test_delete_account_confirm(self, temp_config_with_accounts: Path) -> None:
        """Test confirming account deletion."""
        result = runner.invoke(
            app,
            ["--config-path", str(temp_config_with_accounts), "config", "delete", "--name", "account2"],
            input="y\n",
        )

        assert result.exit_code == 0

        with temp_config_with_accounts.open("r") as f:
            config = yaml.safe_load(f)
        assert "account2" not in config["accounts"]

    def test_delete_default_account(self, temp_config_with_accounts: Path) -> None:
        """Test deleting the default account."""
        result = runner.invoke(
            app, ["--config-path", str(temp_config_with_accounts), "config", "delete", "--name", "account1", "--force"]
        )

        assert result.exit_code == 0

        with temp_config_with_accounts.open("r") as f:
            config = yaml.safe_load(f)
        assert config["default_account"] is None

    def test_delete_nonexistent_account_fails(self, temp_config_with_accounts: Path) -> None:
        """Test deleting nonexistent account fails."""
        result = runner.invoke(
            app,
            ["--config-path", str(temp_config_with_accounts), "config", "delete", "--name", "nonexistent", "--force"],
        )

        assert result.exit_code == 1

    def test_delete_missing_name(self, temp_config_with_accounts: Path) -> None:
        """Test that missing name parameter fails."""
        result = runner.invoke(app, ["--config-path", str(temp_config_with_accounts), "config", "delete", "--force"])

        assert result.exit_code != 0
