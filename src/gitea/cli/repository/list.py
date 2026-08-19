"""List repositories command.

Gitea serves an organization's repositories and a user's at two different
endpoints - `/orgs/{owner}/repos` and `/users/{owner}/repos` - and an owner's
name does not say which of the two it is. `--owner-type` says it, defaulting to
an organization, rather than the command guessing from the name or spending a
request asking the instance what kind of account it found.

The two kinds are an enum rather than a pair of strings compared where they are
used, so the value the option accepts and the value the command branches on
cannot come to differ, and neither kind is the one that "everything else" falls
back to: a value that is neither is refused rather than read as an organization.
"""

from __future__ import annotations

import enum
from typing import Annotated

import typer


class OwnerType(enum.StrEnum):
    """What kind of account `--owner` names, and so which endpoint answers for it."""

    ORGANIZATION = "organization"
    USER = "user"


def list_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner whose repositories are listed.")],
    owner_type: Annotated[
        OwnerType,
        typer.Option(
            "--owner-type",
            help="Whether --owner names an organization or a user account. Gitea serves the two at different endpoints.",
        ),
    ] = OwnerType.ORGANIZATION,
    page: Annotated[
        int | None,
        typer.Option("--page", help="The page number for pagination."),
    ] = None,
    limit: Annotated[
        int | None,
        typer.Option("--limit", help="The number of repositories per page."),
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
    """List the repositories of an owner.

    Args:
        ctx: The Typer context.
        owner: The owner whose repositories are listed.
        owner_type: Whether the owner is an organization or a user account.
        page: The page number for pagination.
        limit: The number of repositories per page.
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
        """List repository information.

        Returns:
            A tuple containing the repository data and metadata.

        """
        # Reading the option through the enum refuses a value that is neither
        # kind, where comparing against one of them would read it as the other.
        kind = OwnerType(owner_type)

        with Gitea(token=token, base_url=base_url) as client:
            return client.repository.list_repositories(
                username=owner if kind is OwnerType.USER else None,
                organization=owner if kind is OwnerType.ORGANIZATION else None,
                page=page,
                limit=limit,
            )

    execute_api_command(api_call=api_call, base_url=base_url, command_name="gitea-cli repo list")
