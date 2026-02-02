"""Tests for the config update CLI command."""

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
def temp_config_with_account(temp_config_file: Path) -> Path:
    """Create a temporary config file with a sample account.

    Args:
        temp_config_file: Temporary config file path.

    Returns:
        Path to the temporary config file.

    """
    config = {
        "accounts": {"test": {"name": "test", "token": "old_token", "base_url": "https://gitea.com"}},
        "default_account": "test",
    }

    with temp_config_file.open("w") as f:
        yaml.safe_dump(config, f)

    return temp_config_file


class TestUpdateCommand:
    """Tests for the update config command."""

    def test_update_command_help(self) -> None:
        """Test update command help."""
        result = runner.invoke(app, ["config", "update", "--help"])
        assert result.exit_code == 0

    def test_update_account_token(self, temp_config_with_account: Path) -> None:
        """Test updating an account token."""
        result = runner.invoke(
            app,
            [
                "--config-path",
                str(temp_config_with_account),
                "config",
                "update",
                "--name",
                "test",
                "--token",
                "new_token",
            ],
        )

        assert result.exit_code == 0
        assert "updated successfully" in result.stderr.lower()

        with temp_config_with_account.open("r") as f:
            config = yaml.safe_load(f)
        assert config["accounts"]["test"]["token"] == "new_token"

    def test_update_account_base_url(self, temp_config_with_account: Path) -> None:
        """Test updating an account base URL."""
        result = runner.invoke(
            app,
            [
                "--config-path",
                str(temp_config_with_account),
                "config",
                "update",
                "--name",
                "test",
                "--base-url",
                "https://gitea.enterprise.com",
            ],
        )

        assert result.exit_code == 0

        with temp_config_with_account.open("r") as f:
            config = yaml.safe_load(f)
        assert config["accounts"]["test"]["base_url"] == "https://gitea.enterprise.com"

    def test_update_account_set_default(self, temp_config_with_account: Path) -> None:
        """Test setting an account as default."""
        # Add another account first
        with temp_config_with_account.open("r") as f:
            config = yaml.safe_load(f)

        config["accounts"]["another"] = {"name": "another", "token": "another_token", "base_url": "https://gitea.com"}

        with temp_config_with_account.open("w") as f:
            yaml.safe_dump(config, f)

        result = runner.invoke(
            app, ["--config-path", str(temp_config_with_account), "config", "update", "--name", "another", "--default"]
        )

        assert result.exit_code == 0

        with temp_config_with_account.open("r") as f:
            config = yaml.safe_load(f)
        assert config["default_account"] == "another"

    def test_update_nonexistent_account_fails(self, temp_config_with_account: Path) -> None:
        """Test updating nonexistent account fails."""
        result = runner.invoke(
            app,
            [
                "--config-path",
                str(temp_config_with_account),
                "config",
                "update",
                "--name",
                "nonexistent",
                "--token",
                "new_token",
            ],
        )

        assert result.exit_code == 1

    def test_update_multiple_fields(self, temp_config_with_account: Path) -> None:
        """Test updating multiple fields at once."""
        result = runner.invoke(
            app,
            [
                "--config-path",
                str(temp_config_with_account),
                "config",
                "update",
                "--name",
                "test",
                "--token",
                "new_token",
                "--base-url",
                "https://new.gitea.com",
            ],
        )

        assert result.exit_code == 0

        with temp_config_with_account.open("r") as f:
            config = yaml.safe_load(f)
        assert config["accounts"]["test"]["token"] == "new_token"
        assert config["accounts"]["test"]["base_url"] == "https://new.gitea.com"

    def test_update_missing_name(self, temp_config_with_account: Path) -> None:
        """Test that missing name parameter fails."""
        result = runner.invoke(
            app, ["--config-path", str(temp_config_with_account), "config", "update", "--token", "new_token"]
        )

        assert result.exit_code != 0
