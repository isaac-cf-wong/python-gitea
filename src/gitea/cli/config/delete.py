"""Delete command for config CLI."""

from __future__ import annotations

from typing import Annotated

import typer


def delete_command(
    ctx: typer.Context,
    name: Annotated[
        str,
        typer.Option("--name", help="Name of the account. It does not need to be the same as the Gitea account name."),
    ],
    force: Annotated[bool, typer.Option("--force", "-f", help="Force deletion without confirmation.")] = False,
) -> None:
    """Delete the configuration of an existing account.

    Args:
        ctx: Typer context.
        name: Name of the account.
        force: Force deletion without confirmation.

    """
    import logging  # noqa: PLC0415

    from gitea.config.manager import ConfigManager  # noqa: PLC0415

    if not force:
        confirm = typer.confirm(f"Are you sure you want to delete the account '{name}'?")
        if not confirm:
            typer.echo("Deletion cancelled.")
            raise typer.Exit()

    logger = logging.getLogger("gitea")

    config_manager = ConfigManager(filename=ctx.obj["config_path"])

    logger.info("Configuration path: %s", config_manager.config_path)

    config_manager.load_config()

    try:
        config_manager.delete_account(name=name)
        config_manager.save_config()
        logger.info("Account '%s' deleted successfully.", name)
    except ValueError as e:
        logger.error("Error deleting account: %s", e)
        raise typer.Exit(code=1) from e
