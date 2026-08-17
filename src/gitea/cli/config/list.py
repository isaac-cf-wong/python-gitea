"""List command for config CLI."""

from __future__ import annotations

import typer


def list_command(ctx: typer.Context) -> None:
    """List all configured accounts.

    Args:
        ctx: Typer context.

    """
    import logging  # noqa: PLC0415

    from gitea.cli.output import emit  # noqa: PLC0415
    from gitea.config.manager import ConfigManager  # noqa: PLC0415

    logger = logging.getLogger("gitea")

    config_manager = ConfigManager(filename=ctx.obj["config_path"])

    logger.info("Configuration path: %s", config_manager.config_path)

    config_manager.load_config()

    accounts = config_manager.config.accounts

    default_account_name = config_manager.config.default_account

    def render_text() -> None:
        """Print the accounts in the human-readable format."""
        if not default_account_name:
            typer.echo("Default account: None")
        else:
            typer.echo(f"Default account: {default_account_name}")

        typer.echo("Configured accounts:")

        for account in accounts.values():
            typer.echo(f"  Name: {account.name}")
            typer.echo(f"    Base URL: {account.base_url}")
            typer.echo("")

    emit(
        ctx,
        data={
            "default_account": default_account_name,
            "accounts": [{"name": account.name, "base_url": account.base_url} for account in accounts.values()],
        },
        metadata={"config_path": str(config_manager.config_path), "account_count": len(accounts)},
        render_text=render_text,
    )
