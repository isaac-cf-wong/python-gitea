"""Tests for the config add CLI command."""

from __future__ import annotations

import json
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


class TestAddCommand:
    """Tests for the add config command."""

    def test_add_command_help(self) -> None:
        """Test add command help."""
        result = runner.invoke(app, ["config", "add", "--help"])
        assert result.exit_code == 0
        assert "add" in result.stdout.lower()

    def test_add_account_successfully(self, temp_config_file: Path) -> None:
        """Test adding an account successfully."""
        result = runner.invoke(
            app,
            [
                "--config-path",
                str(temp_config_file),
                "config",
                "add",
                "--name",
                "test_account",
                "--token",
                "test_token",
            ],
        )

        assert result.exit_code == 0
        assert "added successfully" in result.stderr.lower()

        # Verify the config file was created
        assert temp_config_file.exists()
        with temp_config_file.open("r") as f:
            config = yaml.safe_load(f)
        assert "test_account" in config["accounts"]
        assert config["accounts"]["test_account"]["token"] == "test_token"

    def test_add_account_with_custom_base_url(self, temp_config_file: Path) -> None:
        """Test adding an account with custom base URL."""
        result = runner.invoke(
            app,
            [
                "--config-path",
                str(temp_config_file),
                "config",
                "add",
                "--name",
                "enterprise",
                "--token",
                "enterprise_token",
                "--base-url",
                "https://gitea.enterprise.com",
            ],
        )

        assert result.exit_code == 0

        with temp_config_file.open("r") as f:
            config = yaml.safe_load(f)
        assert config["accounts"]["enterprise"]["base_url"] == "https://gitea.enterprise.com"

    def test_add_account_as_default(self, temp_config_file: Path) -> None:
        """Test adding an account as default."""
        result = runner.invoke(
            app,
            [
                "--config-path",
                str(temp_config_file),
                "config",
                "add",
                "--name",
                "default_account",
                "--token",
                "default_token",
                "--default",
            ],
        )

        assert result.exit_code == 0

        with temp_config_file.open("r") as f:
            config = yaml.safe_load(f)
        assert config["default_account"] == "default_account"

    def test_add_duplicate_account_fails(self, temp_config_file: Path) -> None:
        """Test that adding duplicate account fails."""
        # Add first account
        runner.invoke(
            app, ["--config-path", str(temp_config_file), "config", "add", "--name", "test", "--token", "token1"]
        )

        # Try to add duplicate
        result = runner.invoke(
            app, ["--config-path", str(temp_config_file), "config", "add", "--name", "test", "--token", "token2"]
        )

        assert result.exit_code == 1

    def test_add_missing_required_name(self, temp_config_file: Path) -> None:
        """Test that missing name parameter fails."""
        result = runner.invoke(app, ["--config-path", str(temp_config_file), "config", "add", "--token", "test_token"])

        assert result.exit_code != 0

    def test_add_missing_required_token(self, temp_config_file: Path) -> None:
        """Test that missing token parameter fails."""
        result = runner.invoke(app, ["--config-path", str(temp_config_file), "config", "add", "--name", "test_account"])

        assert result.exit_code != 0

    def test_add_first_account_becomes_default(self, temp_config_file: Path) -> None:
        """Test that first account automatically becomes default."""
        result = runner.invoke(
            app, ["--config-path", str(temp_config_file), "config", "add", "--name", "first", "--token", "first_token"]
        )

        assert result.exit_code == 0

        with temp_config_file.open("r") as f:
            config = yaml.safe_load(f)
        assert config["default_account"] == "first"


class TestAddCommandJsonOutput:
    """Tests for `config add` under `--output json`."""

    def test_json_output_is_the_data_metadata_envelope(self, temp_config_file: Path) -> None:
        """Should report the stored account inside the standard envelope."""
        result = runner.invoke(
            app,
            [
                "--config-path",
                str(temp_config_file),
                "--output",
                "json",
                "config",
                "add",
                "--name",
                "test",
                "--token",
                "test_token",
                "--base-url",
                "https://gitea.example.com/",
            ],
        )

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        # The stored, normalized base URL is reported, not the raw argument.
        assert payload["data"] == {
            "name": "test",
            "base_url": "https://gitea.example.com",
            "is_default": True,
            "status": "added",
        }
        assert payload["metadata"] == {"config_path": str(temp_config_file)}

    def test_json_output_reports_non_default_account(self, temp_config_file: Path) -> None:
        """Should report `is_default` false for an account that is not the default."""
        runner.invoke(
            app,
            ["--config-path", str(temp_config_file), "config", "add", "--name", "first", "--token", "first_token"],
        )

        result = runner.invoke(
            app,
            [
                "--config-path",
                str(temp_config_file),
                "--output",
                "json",
                "config",
                "add",
                "--name",
                "second",
                "--token",
                "second_token",
            ],
        )

        assert result.exit_code == 0
        assert json.loads(result.stdout)["data"]["is_default"] is False

    def test_json_output_omits_the_token(self, temp_config_file: Path) -> None:
        """Should not echo the token back in machine-readable output."""
        result = runner.invoke(
            app,
            [
                "--config-path",
                str(temp_config_file),
                "--output",
                "json",
                "config",
                "add",
                "--name",
                "test",
                "--token",
                "secret_token",
            ],
        )

        assert result.exit_code == 0
        assert "secret_token" not in result.stdout

    def test_no_envelope_on_failure(self, temp_config_file: Path) -> None:
        """Should print no envelope when the account cannot be added."""
        runner.invoke(
            app, ["--config-path", str(temp_config_file), "config", "add", "--name", "test", "--token", "token1"]
        )

        result = runner.invoke(
            app,
            [
                "--config-path",
                str(temp_config_file),
                "--output",
                "json",
                "config",
                "add",
                "--name",
                "test",
                "--token",
                "token2",
            ],
        )

        assert result.exit_code == 1
        assert result.stdout.strip() == ""

    def test_text_output_prints_nothing_on_stdout(self, temp_config_file: Path) -> None:
        """Should leave stdout empty in text mode, as before."""
        result = runner.invoke(
            app, ["--config-path", str(temp_config_file), "config", "add", "--name", "test", "--token", "test_token"]
        )

        assert result.exit_code == 0
        assert result.stdout.strip() == ""
