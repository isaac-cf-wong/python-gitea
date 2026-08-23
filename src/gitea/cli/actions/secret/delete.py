"""Delete an Actions secret of a repository, an organization or the account.

Which scope is asked for follows the usual convention: `--owner` with
`--repository` for a repository's own, `--owner` alone for an organization's, and
neither for those of the authenticated account.
"""

from __future__ import annotations

from typing import Annotated

import typer

from gitea.cli.utils.options import OWNER_SCOPE_HELP, REPOSITORY_SCOPE_HELP, SECRET_NAME_HELP

COMMAND_NAME = "gitea-cli actions secret delete"


def delete_secret_command(
    ctx: typer.Context,
    secret_name: Annotated[str, typer.Option("--secret-name", help=SECRET_NAME_HELP)],
    owner: Annotated[str | None, typer.Option("--owner", help=OWNER_SCOPE_HELP)] = None,
    repository: Annotated[str | None, typer.Option("--repository", help=REPOSITORY_SCOPE_HELP)] = None,
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
    """Delete an Actions secret of a repository, an organization or the account.

    Args:
        ctx: The Typer context.
        secret_name: The name of the secret.
        owner: The owner of the repository, or the organization itself.
        repository: The name of the repository, to narrow the owner to one of its repositories.
        account_name: Name of the account to use for authentication.
        token: Token for authentication.
        base_url: Base URL of the Gitea platform.

    """
    from typing import Any  # noqa: PLC0415

    from gitea.cli.utils.api import execute_api_command  # noqa: PLC0415
    from gitea.cli.utils.auth import get_auth_params  # noqa: PLC0415
    from gitea.cli.utils.options import reporting_scope_errors  # noqa: PLC0415
    from gitea.client.gitea import Gitea  # noqa: PLC0415

    token, base_url = get_auth_params(
        config_path=ctx.obj.get("config_path"),
        account_name=account_name,
        token=token,
        base_url=base_url,
    )

    def api_call() -> tuple[dict[str, Any] | list[dict[str, Any]], dict[str, Any]]:
        """Delete the secret.

        Returns:
            A tuple containing an empty object - the endpoint sends no body - and metadata.

        """
        with reporting_scope_errors(COMMAND_NAME), Gitea(token=token, base_url=base_url) as client:
            return client.actions.delete_secret(
                secret_name=secret_name,
                owner=owner,
                repository=repository,
            )

    execute_api_command(api_call=api_call, base_url=base_url, command_name=COMMAND_NAME)
