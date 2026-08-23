"""List the Actions variables of a repository, an organization or the account.

A variable is the readable counterpart of a secret, so the value comes back with
each entry, under `data`. Anything a workflow must not print belongs in a secret
instead.

Which scope is asked for follows the usual convention: `--owner` with
`--repository` for a repository's own, `--owner` alone for an organization's, and
neither for those of the authenticated account.
"""

from __future__ import annotations

from typing import Annotated

import typer

from gitea.cli.utils.options import OWNER_SCOPE_HELP, REPOSITORY_SCOPE_HELP

COMMAND_NAME = "gitea-cli actions variable list"


def list_variables_command(
    ctx: typer.Context,
    owner: Annotated[str | None, typer.Option("--owner", help=OWNER_SCOPE_HELP)] = None,
    repository: Annotated[str | None, typer.Option("--repository", help=REPOSITORY_SCOPE_HELP)] = None,
    page: Annotated[int | None, typer.Option("--page", help="The page number for pagination.")] = None,
    limit: Annotated[int | None, typer.Option("--limit", help="The number of variables per page.")] = None,
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
    """List the Actions variables of a repository, an organization or the account.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository, or the organization itself.
        repository: The name of the repository, to narrow the owner to one of its repositories.
        page: The page number for pagination.
        limit: The number of variables per page.
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
        """List the variables.

        Returns:
            A tuple containing the variables as a list - this endpoint answers
            with a bare array rather than with a `total_count` object - and metadata.

        """
        with reporting_scope_errors(COMMAND_NAME), Gitea(token=token, base_url=base_url) as client:
            return client.actions.list_variables(
                owner=owner,
                repository=repository,
                page=page,
                limit=limit,
            )

    execute_api_command(api_call=api_call, base_url=base_url, command_name=COMMAND_NAME)
