"""Tests for the configuration manager."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from gitea.config.manager import ConfigManager
from gitea.config.model import AccountConfig


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
def config_manager(temp_config_file: Path) -> ConfigManager:
    """Create a ConfigManager with a temporary config file.

    Args:
        temp_config_file: Temporary config file path.

    Returns:
        ConfigManager instance.

    """
    return ConfigManager(filename=temp_config_file)


class TestConfigManagerInitialization:
    """Tests for ConfigManager initialization."""

    def test_initialize_with_custom_path(self, temp_config_file: Path) -> None:
        """Test ConfigManager initialization with custom path."""
        manager = ConfigManager(filename=temp_config_file)
        assert manager.config_path == temp_config_file

    def test_initialize_creates_parent_directories(self) -> None:
        """Test that initialization creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = Path(tmpdir) / "nested" / "dir" / "config.yaml"
            _manager = ConfigManager(filename=nested_path)
            assert nested_path.parent.exists()

    def test_config_is_none_on_init(self, config_manager: ConfigManager) -> None:
        """Test that _config is None on initialization."""
        assert config_manager._config is None


class TestConfigManagerLoadConfig:
    """Tests for ConfigManager load_config method."""

    def test_load_empty_config_creates_new_config(self, temp_config_file: Path) -> None:
        """Test loading from a non-existent file creates empty config."""
        manager = ConfigManager(filename=temp_config_file)
        manager.load_config()

        assert manager._config is not None
        assert manager._config.accounts == {}
        assert manager._config.default_account is None

    def test_load_config_from_yaml_file(self, temp_config_file: Path) -> None:
        """Test loading configuration from YAML file."""
        config_data = {
            "accounts": {"test": {"name": "test", "token": "test_token", "base_url": "https://gitea.com"}},
            "default_account": "test",
        }

        with temp_config_file.open("w") as f:
            yaml.safe_dump(config_data, f)

        manager = ConfigManager(filename=temp_config_file)
        manager.load_config()

        assert manager._config is not None
        assert "test" in manager.config.accounts
        assert manager.config.accounts["test"].name == "test"
        assert manager.config.default_account == "test"

    def test_load_config_with_invalid_format_raises_error(self, temp_config_file: Path) -> None:
        """Test that loading invalid config raises ValueError."""
        config_data = {
            "accounts": {"test": {"name": "test", "token": "test_token", "base_url": "invalid"}}  # Invalid URL
        }

        with temp_config_file.open("w") as f:
            yaml.safe_dump(config_data, f)

        manager = ConfigManager(filename=temp_config_file)

        with pytest.raises(ValueError, match=r"Invalid configuration format:") as exc_info:
            manager.load_config()
        assert "Invalid configuration format" in str(exc_info.value)


class TestConfigManagerSaveConfig:
    """Tests for ConfigManager save_config method."""

    def test_save_config_to_file(self, config_manager: ConfigManager, temp_config_file: Path) -> None:
        """Test saving configuration to file."""
        config_manager.load_config()
        config_manager.config.accounts["test"] = AccountConfig(name="test", token="test_token")
        config_manager.config.default_account = "test"

        config_manager.save_config()

        # Verify file contents
        with temp_config_file.open("r") as f:
            saved_data = yaml.safe_load(f)

        assert "test" in saved_data["accounts"]
        assert saved_data["accounts"]["test"]["token"] == "test_token"
        assert saved_data["default_account"] == "test"


class TestConfigManagerGetConfig:
    """Tests for ConfigManager get_config method."""

    def test_get_default_config(self, config_manager: ConfigManager) -> None:
        """Test getting default account configuration."""
        config_manager.load_config()
        config_manager.config.accounts["default"] = AccountConfig(name="default", token="default_token")
        config_manager.config.default_account = "default"

        account = config_manager.get_config(None)

        assert account.name == "default"
        assert account.token == "default_token"

    def test_get_specific_config(self, config_manager: ConfigManager) -> None:
        """Test getting specific account configuration."""
        config_manager.load_config()
        config_manager.config.accounts["test"] = AccountConfig(name="test", token="test_token")

        account = config_manager.get_config("test")

        assert account.name == "test"
        assert account.token == "test_token"

    def test_get_nonexistent_config_raises_error(self, config_manager: ConfigManager) -> None:
        """Test that getting nonexistent account raises ValueError."""
        config_manager.load_config()

        with pytest.raises(ValueError, match=r"does not exist in the configuration.") as exc_info:
            config_manager.get_config("nonexistent")
        assert "does not exist" in str(exc_info.value)

    def test_get_config_loads_config_if_needed(self, config_manager: ConfigManager) -> None:
        """Test that get_config loads config if not already loaded."""
        config_manager._config = None  # Explicitly set to None
        config_manager.load_config()
        config_manager.config.accounts["test"] = AccountConfig(name="test", token="test_token")
        config_manager.config.default_account = "test"

        # Create a new manager and verify it loads config
        manager2 = ConfigManager(filename=config_manager.config_path)
        config_manager.save_config()
        account = manager2.get_config(None)

        assert account.name == "test"


class TestConfigManagerAddAccount:
    """Tests for ConfigManager add_account method."""

    def test_add_account_successfully(self, config_manager: ConfigManager) -> None:
        """Test adding an account successfully."""
        config_manager.load_config()
        config_manager.add_account("new_account", "new_token")

        assert "new_account" in config_manager.config.accounts
        assert config_manager.config.accounts["new_account"].token == "new_token"
        assert config_manager.config.default_account == "new_account"

    def test_add_account_with_custom_base_url(self, config_manager: ConfigManager) -> None:
        """Test adding an account with custom base URL."""
        config_manager.load_config()
        config_manager.add_account("enterprise", "enterprise_token", base_url="https://gitea.enterprise.com")

        assert config_manager.config.accounts["enterprise"].base_url == "https://gitea.enterprise.com"

    def test_add_account_as_default(self, config_manager: ConfigManager) -> None:
        """Test adding an account as default."""
        config_manager.load_config()
        config_manager.add_account("account1", "token1")
        config_manager.add_account("account2", "token2", is_default=True)

        assert config_manager.config.default_account == "account2"

    def test_add_duplicate_account_raises_error(self, config_manager: ConfigManager) -> None:
        """Test that adding duplicate account raises ValueError."""
        config_manager.load_config()
        config_manager.add_account("test", "token1")

        with pytest.raises(ValueError, match=r"already exists in the configuration.") as exc_info:
            config_manager.add_account("test", "token2")
        assert "already exists" in str(exc_info.value)

    def test_add_first_account_becomes_default(self, config_manager: ConfigManager) -> None:
        """Test that first account automatically becomes default."""
        config_manager.load_config()
        config_manager.add_account("first", "token1")

        assert config_manager.config.default_account == "first"


class TestConfigManagerUpdateAccount:
    """Tests for ConfigManager update_account method."""

    def test_update_account_token(self, config_manager: ConfigManager) -> None:
        """Test updating an account's token."""
        config_manager.load_config()
        config_manager.add_account("test", "old_token")
        config_manager.update_account("test", token="new_token")

        assert config_manager.config.accounts["test"].token == "new_token"

    def test_update_account_base_url(self, config_manager: ConfigManager) -> None:
        """Test updating an account's base URL."""
        config_manager.load_config()
        config_manager.add_account("test", "token")
        config_manager.update_account("test", base_url="https://new.gitea.com")

        assert config_manager.config.accounts["test"].base_url == "https://new.gitea.com"

    def test_update_account_set_as_default(self, config_manager: ConfigManager) -> None:
        """Test setting an account as default."""
        config_manager.load_config()
        config_manager.add_account("account1", "token1")
        config_manager.add_account("account2", "token2")

        config_manager.update_account("account2", is_default=True)

        assert config_manager._config.default_account == "account2"

    def test_update_account_unset_default(self, config_manager: ConfigManager) -> None:
        """Test unsetting an account as default."""
        config_manager.load_config()
        config_manager.add_account("test", "token")

        config_manager.update_account("test", is_default=False)

        assert config_manager.config.default_account is None

    def test_update_nonexistent_account_raises_error(self, config_manager: ConfigManager) -> None:
        """Test that updating nonexistent account raises ValueError."""
        config_manager.load_config()

        with pytest.raises(ValueError, match=r"does not exist in the configuration.") as exc_info:
            config_manager.update_account("nonexistent", token="token")
        assert "does not exist" in str(exc_info.value)

    def test_update_non_default_account_to_non_default(self, config_manager: ConfigManager) -> None:
        """Test warning when trying to unset default on non-default account."""
        config_manager.load_config()
        config_manager.add_account("account1", "token1")
        config_manager.add_account("account2", "token2")

        # This should not change anything and log a warning
        config_manager.update_account("account2", is_default=False)

        assert config_manager.config.default_account == "account1"


class TestConfigManagerDeleteAccount:
    """Tests for ConfigManager delete_account method."""

    def test_delete_account_successfully(self, config_manager: ConfigManager) -> None:
        """Test deleting an account successfully."""
        config_manager.load_config()
        config_manager.add_account("test", "token")
        config_manager.delete_account("test")

        assert "test" not in config_manager.config.accounts

    def test_delete_default_account(self, config_manager: ConfigManager) -> None:
        """Test deleting the default account."""
        config_manager.load_config()
        config_manager.add_account("test", "token")

        config_manager.delete_account("test")

        assert config_manager.config.default_account is None

    def test_delete_nonexistent_account_raises_error(self, config_manager: ConfigManager) -> None:
        """Test that deleting nonexistent account raises ValueError."""
        config_manager.load_config()

        with pytest.raises(ValueError, match=r"does not exist in the configuration.") as exc_info:
            config_manager.delete_account("nonexistent")
        assert "does not exist" in str(exc_info.value)

    def test_delete_non_default_account(self, config_manager: ConfigManager) -> None:
        """Test deleting a non-default account."""
        config_manager.load_config()
        config_manager.add_account("account1", "token1")
        config_manager.add_account("account2", "token2")

        config_manager.delete_account("account2")

        assert "account2" not in config_manager.config.accounts
        assert config_manager.config.default_account == "account1"


class TestConfigManagerIntegration:
    """Integration tests for ConfigManager."""

    def test_full_workflow(self, config_manager: ConfigManager) -> None:
        """Test a full workflow of operations."""
        # Load empty config
        config_manager.load_config()

        # Add accounts
        config_manager.add_account("personal", "personal_token")
        config_manager.add_account("work", "work_token", base_url="https://gitea.work.com")

        # Update account
        config_manager.update_account("work", is_default=True)

        # Save and verify
        config_manager.save_config()

        # Load in new manager and verify
        manager2 = ConfigManager(filename=config_manager.config_path)
        manager2.load_config()

        assert len(manager2.config.accounts) == 2  # noqa: PLR2004
        assert manager2.config.default_account == "work"
        assert manager2.get_config(None).name == "work"

    def test_persistence_across_instances(self, config_manager: ConfigManager) -> None:
        """Test that configuration persists across different manager instances."""
        config_manager.load_config()
        config_manager.add_account("test", "test_token")
        config_manager.save_config()

        # Create new manager from same file
        manager2 = ConfigManager(filename=config_manager.config_path)
        manager2.load_config()

        account = manager2.get_config("test")
        assert account.token == "test_token"


class TestConfigManagerHasDefaultAccount:
    """Tests for ConfigManager has_default_account method."""

    def test_has_default_account_returns_true_when_set(self, config_manager: ConfigManager) -> None:
        """Test that has_default_account returns True when a default account is set."""
        config_manager.load_config()
        config_manager.add_account("test", "test_token")

        assert config_manager.has_default_account() is True

    def test_has_default_account_returns_false_when_not_set(self, config_manager: ConfigManager) -> None:
        """Test that has_default_account returns False when no default account is set."""
        config_manager.load_config()

        assert config_manager.has_default_account() is False

    def test_has_default_account_loads_config_if_needed(
        self, config_manager: ConfigManager, temp_config_file: Path
    ) -> None:
        """Test that has_default_account loads config if _config is None."""
        # Create a config file with a default account
        config_data = {
            "accounts": {"test": {"name": "test", "token": "test_token", "base_url": "https://gitea.com"}},
            "default_account": "test",
        }

        with temp_config_file.open("w") as f:
            yaml.safe_dump(config_data, f)

        # Create new manager (without loading)
        manager = ConfigManager(filename=temp_config_file)
        assert manager._config is None

        # Call has_default_account which should load the config
        result = manager.has_default_account()

        assert manager._config is not None
        assert result is True

    def test_has_default_account_returns_false_after_deleting_default(self, config_manager: ConfigManager) -> None:
        """Test that has_default_account returns False after deleting the default account."""
        config_manager.load_config()
        config_manager.add_account("test", "test_token")

        assert config_manager.has_default_account() is True

        config_manager.delete_account("test")

        assert config_manager.has_default_account() is False

    def test_has_default_account_returns_true_after_unsetting_then_setting_default(
        self, config_manager: ConfigManager
    ) -> None:
        """Test has_default_account after unsetting and then setting a new default."""
        config_manager.load_config()
        config_manager.add_account("account1", "token1")
        config_manager.add_account("account2", "token2")

        # account1 is default
        assert config_manager.has_default_account() is True

        # Unset default
        config_manager.update_account("account1", is_default=False)
        assert config_manager.has_default_account() is False

        # Set new default
        config_manager.update_account("account2", is_default=True)
        assert config_manager.has_default_account() is True
