"""Get the token a new Actions runner joins a scope with.

Registering a runner is not something this API does: the token is what
`act_runner register` is then given, and the runner joins over the Actions
protocol. So the sequence is to take a token here, register the machine out of
band, and then list what appeared.

The token belongs to the scope rather than to one runner - every runner
registered with it lands in that scope - and it is a credential: anything holding
it can attach a machine that will execute the scope's jobs. It is printed, so
redirect it rather than leaving it in a shell history or a CI log.
"""

from __future__ import annotations

from typing import Annotated

import typer

from gitea.cli.utils.options import ADMIN_HELP, OWNER_SCOPE_HELP, REPOSITORY_SCOPE_HELP

COMMAND_NAME = "gitea-cli actions runner registration-token"


def runner_registration_token_command(
    ctx: typer.Context,
    owner: Annotated[str | None, typer.Option("--owner", help=OWNER_SCOPE_HELP)] = None,
    repository: Annotated[str | None, typer.Option("--repository", help=REPOSITORY_SCOPE_HELP)] = None,
    admin: Annotated[bool, typer.Option("--admin", help=ADMIN_HELP)] = False,
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
    """Get the token a new Actions runner joins a scope with.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository, or the organization itself.
        repository: The name of the repository, to narrow the owner to one of its repositories.
        admin: Whether to address the whole instance.
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
        """Ask for the scope's registration token.

        Returns:
            A tuple containing the token, under `token`, and metadata.

        """
        with reporting_scope_errors(COMMAND_NAME), Gitea(token=token, base_url=base_url) as client:
            return client.actions.create_runner_registration_token(
                owner=owner,
                repository=repository,
                admin=admin,
            )

    execute_api_command(api_call=api_call, base_url=base_url, command_name=COMMAND_NAME)
