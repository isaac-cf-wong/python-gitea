"""Tests for the config update CLI command."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from gitea.cli.main import app
from tests.cli.envelope import parse_envelope
from tests.cli.rendering import unrendered

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
        # The words of the message are asserted one by one, and with rich's
        # styling and layout removed: `RichHandler` appends the emitting frame at
        # the right of a record's first line, so at a narrow terminal width it
        # lands between the words of a message that wraps.
        message = unrendered(result.stderr).lower()
        assert "updated" in message
        assert "successfully" in message

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


class TestUpdateCommandJsonOutput:
    """Tests for `config update` under `--output json`."""

    def test_json_output_is_the_data_metadata_envelope(self, temp_config_with_account: Path) -> None:
        """Should report the updated fields inside the standard envelope."""
        result = runner.invoke(
            app,
            [
                "--config-path",
                str(temp_config_with_account),
                "--output",
                "json",
                "config",
                "update",
                "--name",
                "test",
                "--base-url",
                "https://new.gitea.com",
            ],
        )

        assert result.exit_code == 0
        payload = parse_envelope(result.stdout)
        assert payload["data"] == {
            "name": "test",
            "base_url": "https://new.gitea.com",
            "is_default": True,
            "updated_fields": ["base_url"],
            "status": "updated",
        }
        assert payload["metadata"] == {"config_path": str(temp_config_with_account)}

    def test_json_output_lists_every_updated_field(self, temp_config_with_account: Path) -> None:
        """Should list each field the command changed."""
        result = runner.invoke(
            app,
            [
                "--config-path",
                str(temp_config_with_account),
                "--output",
                "json",
                "config",
                "update",
                "--name",
                "test",
                "--token",
                "new_token",
                "--base-url",
                "https://new.gitea.com",
                "--default",
            ],
        )

        assert result.exit_code == 0
        assert parse_envelope(result.stdout)["data"]["updated_fields"] == ["token", "base_url", "default_account"]

    def test_json_output_with_no_changes(self, temp_config_with_account: Path) -> None:
        """Should report an empty field list when nothing was changed."""
        result = runner.invoke(
            app,
            [
                "--config-path",
                str(temp_config_with_account),
                "--output",
                "json",
                "config",
                "update",
                "--name",
                "test",
            ],
        )

        assert result.exit_code == 0
        assert parse_envelope(result.stdout)["data"]["updated_fields"] == []

    def test_json_output_omits_the_token(self, temp_config_with_account: Path) -> None:
        """Should not echo the new token back in machine-readable output."""
        result = runner.invoke(
            app,
            [
                "--config-path",
                str(temp_config_with_account),
                "--output",
                "json",
                "config",
                "update",
                "--name",
                "test",
                "--token",
                "secret_token",
            ],
        )

        assert result.exit_code == 0
        assert "secret_token" not in result.stdout

    def test_no_envelope_on_failure(self, temp_config_with_account: Path) -> None:
        """Should print no envelope when the account does not exist."""
        result = runner.invoke(
            app,
            [
                "--config-path",
                str(temp_config_with_account),
                "--output",
                "json",
                "config",
                "update",
                "--name",
                "nonexistent",
                "--token",
                "new_token",
            ],
        )

        assert result.exit_code == 1
        assert result.stdout.strip() == ""

    def test_text_output_prints_nothing_on_stdout(self, temp_config_with_account: Path) -> None:
        """Should leave stdout empty in text mode, as before."""
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
        assert result.stdout.strip() == ""
