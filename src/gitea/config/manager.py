"""Configuration manager for gitea."""

from __future__ import annotations

import logging
from pathlib import Path

import platformdirs
import yaml

from gitea.config.model import AccountConfig, Config

logger = logging.getLogger("gitea")


class ConfigManager:
    """Configuration manager for gitea."""

    def __init__(self, filename: Path | str | None = None) -> None:
        """Initialize ConfigManager.

        Args:
            filename: Name of the configuration file.

        """
        filename = filename or Path(platformdirs.user_config_dir(appname="gitea")) / "config.yaml"
        filename = Path(filename)
        filename.parent.mkdir(parents=True, exist_ok=True)
        self.config_path = filename
        self._config: Config | None = None

    @property
    def config(self) -> Config:
        """Get the current configuration.

        Returns:
            Config: Current configuration.

        """
        if self._config is None:
            self._config = self._load_config()
        return self._config

    @config.setter
    def config(self, value: Config) -> None:
        """Set the current configuration.

        Args:
            value: New configuration to set.

        """
        self._config = value

    def get_config(self, name: str | None) -> AccountConfig:
        """Get the configuration for a specific account.

        Args:
            name: Name of the account. If None, the default account is used.

        Returns:
            AccountConfig: Configuration of the specified account.

        """
        if self._config is None:
            self.load_config()

        name = self.config.default_account if name is None else name

        if self._config is None:
            self.load_config()

        if name not in self.config.accounts:
            raise ValueError(f"Account '{name}' does not exist in the configuration.")

        return self.config.accounts[name]

    def add_account(self, name: str, token: str, base_url: str = "https://gitea.com", is_default: bool = False) -> None:
        """Add a new account to the configuration.

        Args:
            name: Name of the account.
            token: Authentication token for the account.
            base_url: Base URL of the Gitea platform.
            is_default: Set as default account.

        """
        if self._config is None:
            self.load_config()

        if name in self.config.accounts:
            raise ValueError(f"Account '{name}' already exists in the configuration.")

        self.config.accounts[name] = AccountConfig(name=name, token=token, base_url=base_url)

        if is_default or len(self.config.accounts) == 1:
            self.config.default_account = name

    def update_account(
        self,
        name: str,
        token: str | None = None,
        base_url: str | None = None,
        is_default: bool | None = None,
    ) -> None:
        """Update an existing account in the configuration.

        Args:
            name: Name of the account to update.
            token: New authentication token for the account (optional).
            base_url: New base URL of the account (optional).
            is_default: Set as default account (optional).

        """
        if self._config is None:
            self.load_config()

        if name not in self.config.accounts:
            raise ValueError(f"Account '{name}' does not exist in the configuration.")

        account = self.config.accounts[name]

        if token is not None:
            account.token = token
        if base_url is not None:
            account.base_url = base_url

        if is_default is not None:
            if is_default:
                self.config.default_account = name
            elif self.config.default_account == name:
                self.config.default_account = None
            else:
                logger.warning("Account '%s' is not the default account. No changes made to default account.", name)

    def delete_account(self, name: str) -> None:
        """Delete an account from the configuration.

        Args:
            name: Name of the account to delete.

        """
        if self._config is None:
            self.load_config()

        if name not in self.config.accounts:
            raise ValueError(f"Account '{name}' does not exist in the configuration.")

        del self.config.accounts[name]

        if self.config.default_account == name:
            self.config.default_account = None

    def _load_config(self, filename: Path | str | None = None) -> Config:
        """Load configuration from the YAML file.

        Args:
            filename: Optional path to the configuration file.

        Returns:
            Config: Loaded configuration.

        """
        filename = filename or self.config_path
        filename = Path(filename)
        if not filename.exists():
            return Config()

        with filename.open("r", encoding="utf-8") as file:
            raw_config = yaml.safe_load(file) or {}

        try:
            return Config(**raw_config)
        except ValueError as e:
            raise ValueError(f"Invalid configuration format: {e}") from e

    def load_config(self, filename: Path | str | None = None) -> None:
        """Load configuration from the YAML file.

        Args:
            filename: Optional path to the configuration file.

        """
        self.config = self._load_config(filename)

    def save_config(self, filename: Path | str | None = None) -> None:
        """Save configuration to the YAML file.

        Args:
            filename: Optional path to the configuration file.

        """
        filename = filename or self.config_path
        filename = Path(filename)
        with filename.open("w", encoding="utf-8") as file:
            yaml.safe_dump(self.config.model_dump(), file)

    def has_default_account(self) -> bool:
        """Check if a default account is set.

        Returns:
            bool: True if a default account is set, False otherwise.

        """
        if self._config is None:
            self.load_config()

        return self.config.default_account is not None
