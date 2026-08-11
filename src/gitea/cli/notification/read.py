"""Read notifications command."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

import typer


def read_command(
    ctx: typer.Context,
    owner: Annotated[
        str | None,
        typer.Option("--owner", help="Owner of the repository. If omitted, marks the user's notifications."),
    ] = None,
    repository: Annotated[
        str | None,
        typer.Option("--repository", help="Name of the repository. Requires --owner."),
    ] = None,
    last_read_at: Annotated[
        datetime | None,
        typer.Option("--last-read-at", help="Last point that notifications were checked."),
    ] = None,
    all_notifications: Annotated[
        bool | None,
        typer.Option("--all", help="Mark all notifications on this repo."),
    ] = None,
    status_types: Annotated[
        list[str] | None,
        typer.Option("--status-type", help="Mark notifications with the provided status types as read."),
    ] = None,
    to_status: Annotated[
        str | None,
        typer.Option("--to-status", help="Status to mark notifications as."),
    ] = None,
    account_name: Annotated[
        str | None,
        typer.Option(
            "--account-name",
            help="Name of the account to use for authentication.",
        ),
    ] = None,
    token: Annotated[
        str | None,
        typer.Option(
            "--token",
            help="Token for authentication. If not provided, the token from the specified account will be used.",
        ),
    ] = None,
    base_url: Annotated[
        str | None,
        typer.Option(
            "--base-url",
            help="Base URL of the Gitea platform. If not provided, the base URL from the specified account will be used.",
        ),
    ] = None,
) -> None:
    """Mark notifications as read.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository.
        last_read_at: Last point that notifications were checked.
        all_notifications: Mark all notifications on this repo.
        status_types: Mark notifications with the provided status types as read.
        to_status: Status to mark notifications as.
        account_name: Name of the account to use for authentication.
        token: Token for authentication.
        base_url: Base URL of the Gitea platform.

    """
    from typing import Any  # noqa: PLC0415

    from gitea.cli.utils.api import execute_api_command  # noqa: PLC0415
    from gitea.cli.utils.auth import get_auth_params  # noqa: PLC0415
    from gitea.client.gitea import Gitea  # noqa: PLC0415

    token, base_url = get_auth_params(
        config_path=ctx.obj.get("config_path"),
        account_name=account_name,
        token=token,
        base_url=base_url,
    )

    def api_call() -> tuple[dict[str, Any] | list[dict[str, Any]], dict[str, Any]]:
        """Read notification information.

        Returns:
            A tuple containing the response data and metadata.

        """
        with Gitea(token=token, base_url=base_url) as client:
            if owner is not None and repository is not None:
                return client.notification.read_repo_notifications(
                    owner=owner,
                    repository=repository,
                    last_read_at=last_read_at,
                    all_notifications=all_notifications,
                    status_types=status_types,
                    to_status=to_status,
                )
            return client.notification.read_notifications(
                last_read_at=last_read_at,
                all_notifications=all_notifications,
                status_types=status_types,
                to_status=to_status,
            )

    execute_api_command(api_call=api_call, command_name="gitea-cli notification read")
