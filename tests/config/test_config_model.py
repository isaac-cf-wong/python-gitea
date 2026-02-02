"""Tests for the configuration model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from gitea.config.model import AccountConfig, Config


class TestAccountConfig:
    """Tests for AccountConfig model."""

    def test_create_account_config_with_defaults(self) -> None:
        """Test creating an AccountConfig with default base_url."""
        account = AccountConfig(name="test_account", token="test_token")
        assert account.name == "test_account"
        assert account.token == "test_token"
        assert account.base_url == "https://gitea.com"

    def test_create_account_config_with_custom_base_url(self) -> None:
        """Test creating an AccountConfig with custom base_url."""
        account = AccountConfig(name="enterprise", token="enterprise_token", base_url="https://gitea.enterprise.com")
        assert account.name == "enterprise"
        assert account.token == "enterprise_token"
        assert account.base_url == "https://gitea.enterprise.com"

    def test_base_url_must_start_with_http(self) -> None:
        """Test that base_url must start with http:// or https://."""
        with pytest.raises(ValidationError) as exc_info:
            AccountConfig(name="test", token="token", base_url="gitea.com")
        assert "base_url must start with http:// or https://" in str(exc_info.value)

    def test_base_url_must_start_with_https(self) -> None:
        """Test that base_url can start with https://."""
        account = AccountConfig(name="test", token="token", base_url="https://gitea.com")
        assert account.base_url == "https://gitea.com"

    def test_base_url_strips_trailing_slash(self) -> None:
        """Test that base_url strips trailing slashes."""
        account = AccountConfig(name="test", token="token", base_url="https://gitea.com/")
        assert account.base_url == "https://gitea.com"

    def test_base_url_strips_multiple_trailing_slashes(self) -> None:
        """Test that base_url strips multiple trailing slashes."""
        account = AccountConfig(name="test", token="token", base_url="https://gitea.com///")
        assert account.base_url == "https://gitea.com"

    def test_account_config_repr(self) -> None:
        """Test the string representation of AccountConfig."""
        account = AccountConfig(name="test_account", token="token", base_url="https://gitea.com")
        assert repr(account) == "AccountConfig(name=test_account, base_url=https://gitea.com)"

    def test_account_config_missing_required_fields(self) -> None:
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            AccountConfig(name="test")  # Missing token

        with pytest.raises(ValidationError):
            AccountConfig(token="token")  # Missing name


class TestConfig:
    """Tests for Config model."""

    def test_create_empty_config(self) -> None:
        """Test creating an empty Config."""
        config = Config()
        assert config.accounts == {}
        assert config.default_account is None

    def test_create_config_with_accounts(self) -> None:
        """Test creating a Config with accounts."""
        account1 = AccountConfig(name="account1", token="token1")
        account2 = AccountConfig(name="account2", token="token2")

        config = Config(accounts={"account1": account1, "account2": account2}, default_account="account1")

        assert len(config.accounts) == 2  # noqa: PLR2004
        assert config.accounts["account1"].name == "account1"
        assert config.accounts["account2"].name == "account2"
        assert config.default_account == "account1"

    def test_config_serialization(self) -> None:
        """Test that Config can be serialized and deserialized."""
        account = AccountConfig(name="test", token="token123")
        config = Config(accounts={"test": account}, default_account="test")

        config_dict = config.model_dump()

        assert config_dict["accounts"]["test"]["name"] == "test"
        assert config_dict["accounts"]["test"]["token"] == "token123"
        assert config_dict["default_account"] == "test"

    def test_config_deserialization(self) -> None:
        """Test that Config can be deserialized from dict."""
        config_dict = {
            "accounts": {"test": {"name": "test", "token": "token123", "base_url": "https://gitea.com"}},
            "default_account": "test",
        }

        config = Config(**config_dict)

        assert "test" in config.accounts
        assert config.accounts["test"].name == "test"
        assert config.default_account == "test"
