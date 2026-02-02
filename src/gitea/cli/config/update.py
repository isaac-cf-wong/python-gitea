"""Update command for config CLI."""

from __future__ import annotations

from typing import Annotated

import typer


def update_command(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", help="Name of the account.")],
    token: Annotated[str | None, typer.Option("--token", help="Token for authentication.")] = None,
    base_url: Annotated[str | None, typer.Option("--base-url", help="Base URL of the Gitea platform.")] = None,
    default: Annotated[bool | None, typer.Option("--default", help="Set as default account.")] = None,
) -> None:
    """Update the configuration of an existing platform.

    Args:
        ctx: Typer context.
        name: Name of the account.
        token: Token for authentication.
        base_url: Base URL of the platform.
        default: Set as default account.

    """
    import logging  # noqa: PLC0415

    from gitea.config.manager import ConfigManager  # noqa: PLC0415

    logger = logging.getLogger("gitea")

    config_manager = ConfigManager(filename=ctx.obj["config_path"])

    logger.info("Configuration path: %s", config_manager.config_path)

    config_manager.load_config()

    try:
        config_manager.update_account(name=name, token=token, base_url=base_url, is_default=default)
        config_manager.save_config()
        updated_entries = []
        if token is not None:
            updated_entries.append("token")
        if base_url is not None:
            updated_entries.append("base_url")
        if default is not None:
            updated_entries.append("default_account")
        if updated_entries:
            logger.info(
                "Account '%s' updated successfully. Updated fields: %s",
                name,
                ", ".join(updated_entries),
            )
        else:
            logger.info("Account '%s' updated successfully. No fields changed.", name)
    except ValueError as e:
        logger.error("Error updating account: %s", e)
        raise typer.Exit(code=1) from e
