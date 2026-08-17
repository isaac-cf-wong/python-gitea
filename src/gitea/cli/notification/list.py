"""List notifications command."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

import typer


def list_command(
    ctx: typer.Context,
    owner: Annotated[
        str | None,
        typer.Option("--owner", help="Owner of the repository. If omitted, lists the user's notifications."),
    ] = None,
    repository: Annotated[
        str | None,
        typer.Option("--repository", help="Name of the repository. Requires --owner."),
    ] = None,
    all_notifications: Annotated[
        bool | None,
        typer.Option("--all", help="Show notifications marked as read."),
    ] = None,
    status_types: Annotated[
        list[str] | None,
        typer.Option("--status-type", help="Show notifications with the provided status types."),
    ] = None,
    subject_type: Annotated[
        list[str] | None,
        typer.Option("--subject-type", help="Filter notifications by subject type."),
    ] = None,
    since: Annotated[
        datetime | None,
        typer.Option("--since", help="Only show notifications updated after the given time."),
    ] = None,
    before: Annotated[
        datetime | None,
        typer.Option("--before", help="Only show notifications updated before the given time."),
    ] = None,
    page: Annotated[
        int | None,
        typer.Option("--page", help="The page number for pagination."),
    ] = None,
    limit: Annotated[
        int | None,
        typer.Option("--limit", help="The number of notifications per page."),
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
    """List notifications.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository.
        all_notifications: Show notifications marked as read.
        status_types: Show notifications with the provided status types.
        subject_type: Filter notifications by subject type.
        since: Only show notifications updated after the given time.
        before: Only show notifications updated before the given time.
        page: The page number for pagination.
        limit: The number of notifications per page.
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

    if (owner is None) != (repository is None):
        raise typer.BadParameter(
            "Both --owner and --repository must be provided together, or neither "
            "to list the authenticated user's notifications."
        )

    def api_call() -> tuple[dict[str, Any] | list[dict[str, Any]], dict[str, Any]]:
        """List notification information.

        Returns:
            A tuple containing the notification data and metadata.

        """
        with Gitea(token=token, base_url=base_url) as client:
            if owner is not None and repository is not None:
                return client.notification.list_repo_notifications(
                    owner=owner,
                    repository=repository,
                    all_notifications=all_notifications,
                    status_types=status_types,
                    subject_type=subject_type,
                    since=since,
                    before=before,
                    page=page,
                    limit=limit,
                )
            return client.notification.list_notifications(
                all_notifications=all_notifications,
                status_types=status_types,
                subject_type=subject_type,
                since=since,
                before=before,
                page=page,
                limit=limit,
            )

    execute_api_command(api_call=api_call, base_url=base_url, command_name="gitea-cli notification list")
