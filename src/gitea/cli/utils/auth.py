"""Utilities for authentication in the CLI."""

from __future__ import annotations

import logging
from pathlib import Path

from gitea.config.manager import ConfigManager

logger = logging.getLogger("gitea")


def get_auth_params(
    config_path: Path | str,
    account_name: str | None,
    token: str | None,
    base_url: str | None,
) -> tuple[str, str]:
    """Get authentication parameters from CLI context.

    Args:
        config_path: Path to the configuration file.
        account_name: Name of the account to use for authentication.
        token: Token for authentication.
        base_url: Base URL of the GitHub platform.

    Returns:
        A tuple containing the token and base URL for authentication.

    """
    if account_name is not None:
        if token is not None or base_url is not None:
            logger.warning(
                "Both account name and token/base_url provided. The token and base_url from the account '%s' will be used.",
                account_name,
            )

        config_manager = ConfigManager(filename=config_path)
        config_manager.load_config()
        account_config = config_manager.get_config(name=account_name)
        token = account_config.token
        base_url = account_config.base_url
        return token, base_url
    if token is None and base_url is None:
        config_manager = ConfigManager(filename=config_path)
        config_manager.load_config()

        if config_manager.has_default_account():
            account_config = config_manager.get_config(name=None)
            token = account_config.token
            base_url = account_config.base_url
            return token, base_url
        else:
            raise ValueError(
                "No default account available for authentication. Please provide an account name or token/base_url."
            )
    if token is None or base_url is None:
        missing_params = []
        if token is None:
            missing_params.append("token")
        if base_url is None:
            missing_params.append("base_url")
        raise ValueError(
            f"Insufficient authentication parameters. Missing: {', '.join(missing_params)}. "
            f"Please provide both token and base_url, or use an account name."
        )
    return token, base_url
