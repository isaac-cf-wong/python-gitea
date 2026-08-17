"""Tests for the config delete CLI command."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from gitea.cli.main import app
from tests.cli.envelope import parse_envelope

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


class TestDeleteCommandJsonOutput:
    """Tests for `config delete` under `--output json`."""

    def test_json_output_is_the_data_metadata_envelope(self, temp_config_with_accounts: Path) -> None:
        """Should report the deleted account inside the standard envelope."""
        result = runner.invoke(
            app,
            [
                "--config-path",
                str(temp_config_with_accounts),
                "--output",
                "json",
                "config",
                "delete",
                "--name",
                "account2",
                "--force",
            ],
        )

        assert result.exit_code == 0
        payload = parse_envelope(result.stdout)
        assert payload["data"] == {"name": "account2", "status": "deleted"}
        assert payload["metadata"] == {"config_path": str(temp_config_with_accounts)}

    def test_json_output_when_cancelled(self, temp_config_with_accounts: Path) -> None:
        """Should report the cancellation as an envelope, not as prose."""
        result = runner.invoke(
            app,
            [
                "--config-path",
                str(temp_config_with_accounts),
                "--output",
                "json",
                "config",
                "delete",
                "--name",
                "account2",
            ],
            input="n\n",
        )

        assert result.exit_code == 0
        # The confirmation prompt goes to stderr in JSON mode, so it cannot break
        # a consumer parsing stdout. CliRunner itself echoes the typed answer into
        # stdout, which a real non-interactive consumer never sees.
        assert "Are you sure" not in result.stdout
        assert "Are you sure" in result.stderr

        # `" n\n"` is CliRunner's echo of the answer typed at the prompt - the
        # only text allowed on stdout besides the envelope. Declaring it exactly
        # is what makes a leaked log line or rendering fail here.
        payload = parse_envelope(result.stdout, allow_prefix=" n\n")
        assert payload["data"] == {"name": "account2", "status": "cancelled"}
        assert payload["metadata"] == {}
        assert "Deletion cancelled." not in result.stdout

        with temp_config_with_accounts.open("r") as f:
            config = yaml.safe_load(f)
        assert "account2" in config["accounts"]

    def test_no_envelope_on_failure(self, temp_config_with_accounts: Path) -> None:
        """Should print no envelope when the account does not exist."""
        result = runner.invoke(
            app,
            [
                "--config-path",
                str(temp_config_with_accounts),
                "--output",
                "json",
                "config",
                "delete",
                "--name",
                "nonexistent",
                "--force",
            ],
        )

        assert result.exit_code == 1
        assert result.stdout.strip() == ""

    def test_text_output_keeps_the_cancellation_message(self, temp_config_with_accounts: Path) -> None:
        """Should keep the human-readable cancellation message in text mode."""
        result = runner.invoke(
            app,
            ["--config-path", str(temp_config_with_accounts), "config", "delete", "--name", "account2"],
            input="n\n",
        )

        assert result.exit_code == 0
        assert "Deletion cancelled." in result.stdout
        # Text mode keeps prompting on stdout, as it did before.
        assert "Are you sure" in result.stdout
