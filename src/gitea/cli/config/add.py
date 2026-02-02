"""Add command for config CLI."""

from __future__ import annotations

from typing import Annotated

import typer


def add_command(
    ctx: typer.Context,
    name: Annotated[
        str,
        typer.Option("--name", help="Name of the account. It does not need to be the same as the Gitea account name."),
    ],
    token: Annotated[str, typer.Option("--token", help="Token for authentication.")],
    base_url: Annotated[str, typer.Option("--base-url", help="Base URL of the platform.")] = "https://gitea.com",
    is_default: Annotated[bool, typer.Option("--default", help="Set as default account.")] = False,
) -> None:
    """Add a new account to the configuration.

    Args:
        ctx: Typer context.
        name: Name of the account. It does not need to be the same as the Gitea account name.
        token: Token for authentication.
        base_url: Base URL of the platform.
        is_default: Set as default account.

    """
    import logging  # noqa: PLC0415

    from gitea.config.manager import ConfigManager  # noqa: PLC0415

    logger = logging.getLogger("gitea")

    config_manager = ConfigManager(filename=ctx.obj["config_path"])

    logger.info("Configuration path: %s", config_manager.config_path)

    config_manager.load_config()

    try:
        config_manager.add_account(name=name, token=token, base_url=base_url, is_default=is_default)
        config_manager.save_config()
        logger.info("Account '%s' added successfully.", name)
    except ValueError as e:
        logger.error("Error adding account: %s", e)
        raise typer.Exit(code=1) from e
