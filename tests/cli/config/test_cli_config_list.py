"""Tests for the config list CLI command."""

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


class TestListCommand:
    """Tests for the list config command."""

    def test_list_command_help(self) -> None:
        """Test list command help."""
        result = runner.invoke(app, ["config", "list", "--help"])
        assert result.exit_code == 0

    def test_list_empty_config(self, temp_config_file: Path) -> None:
        """Test listing accounts when none exist."""
        result = runner.invoke(app, ["--config-path", str(temp_config_file), "config", "list"])

        assert result.exit_code == 0
        assert "configured accounts" in result.stdout.lower()

    def test_list_accounts_shows_default(self, temp_config_with_accounts: Path) -> None:
        """Test that default account is shown."""
        result = runner.invoke(app, ["--config-path", str(temp_config_with_accounts), "config", "list"])

        assert result.exit_code == 0
        assert "Default account: account1" in result.stdout
        assert "configured accounts" in result.stdout.lower()

    def test_list_accounts_shows_all_accounts(self, temp_config_with_accounts: Path) -> None:
        """Test that all accounts are shown."""
        result = runner.invoke(app, ["--config-path", str(temp_config_with_accounts), "config", "list"])

        assert result.exit_code == 0
        assert "account1" in result.stdout
        assert "account2" in result.stdout

    def test_list_accounts_shows_base_urls(self, temp_config_with_accounts: Path) -> None:
        """Test that base URLs are shown."""
        result = runner.invoke(app, ["--config-path", str(temp_config_with_accounts), "config", "list"])

        assert result.exit_code == 0
        # Use regex to match complete URLs in context
        import re  # noqa: PLC0415

        assert re.search(r"account1.*https://gitea\.com", result.stdout, re.DOTALL)
        assert re.search(r"account2.*https://gitea\.enterprise\.com", result.stdout, re.DOTALL)

    def test_list_no_default_account(self, temp_config_file: Path) -> None:
        """Test listing when no default account is set."""
        config = {
            "accounts": {"account1": {"name": "account1", "token": "token1", "base_url": "https://gitea.com"}},
            "default_account": None,
        }

        with temp_config_file.open("w") as f:
            yaml.safe_dump(config, f)

        result = runner.invoke(app, ["--config-path", str(temp_config_file), "config", "list"])

        assert result.exit_code == 0
        assert "Default account: None" in result.stdout
