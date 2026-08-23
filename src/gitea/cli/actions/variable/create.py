"""Create an Actions variable of a repository, an organization or the account.

Creating and updating are two endpoints here, where setting a secret is one: a
name that already exists is reported as a conflict rather than being overwritten.
So this never replaces a value by accident, and
`gitea-cli actions variable update` is how one is replaced on purpose.

Which scope is asked for follows the usual convention: `--owner` with
`--repository` for a repository's own, `--owner` alone for an organization's, and
neither for those of the authenticated account.
"""

from __future__ import annotations

from typing import Annotated

import typer

from gitea.cli.utils.options import OWNER_SCOPE_HELP, REPOSITORY_SCOPE_HELP, VARIABLE_NAME_HELP

COMMAND_NAME = "gitea-cli actions variable create"


def create_variable_command(
    ctx: typer.Context,
    variable_name: Annotated[str, typer.Option("--variable-name", help=VARIABLE_NAME_HELP)],
    value: Annotated[str, typer.Option("--value", help="Value to store in the variable.")],
    owner: Annotated[str | None, typer.Option("--owner", help=OWNER_SCOPE_HELP)] = None,
    repository: Annotated[str | None, typer.Option("--repository", help=REPOSITORY_SCOPE_HELP)] = None,
    description: Annotated[
        str | None, typer.Option("--description", help="What the variable is for, shown alongside it in the web UI.")
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
    """Create an Actions variable of a repository, an organization or the account.

    Args:
        ctx: The Typer context.
        variable_name: The name of the variable.
        value: The value to store.
        owner: The owner of the repository, or the organization itself.
        repository: The name of the repository, to narrow the owner to one of its repositories.
        description: What the variable is for.
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
        """Create the variable.

        Returns:
            A tuple containing an empty object - the endpoint sends no body - and metadata.

        """
        with reporting_scope_errors(COMMAND_NAME), Gitea(token=token, base_url=base_url) as client:
            return client.actions.create_variable(
                variable_name=variable_name,
                value=value,
                owner=owner,
                repository=repository,
                description=description,
            )

    execute_api_command(api_call=api_call, base_url=base_url, command_name=COMMAND_NAME)
