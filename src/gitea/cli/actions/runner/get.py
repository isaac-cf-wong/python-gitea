"""Get one Actions runner of a repository, an organization, an account or the instance.

A runner is addressed through the scope it is registered to, so asking for a real
runner through a scope it does not belong to is reported as not found: the ID
exists, the runner is simply not that scope's.

`labels` is what a job's `runs-on` is matched against, and is the usual reason a
job sits queued while a runner sits idle.
"""

from __future__ import annotations

from typing import Annotated

import typer

from gitea.cli.utils.options import ADMIN_HELP, OWNER_SCOPE_HELP, REPOSITORY_SCOPE_HELP, RUNNER_ID_HELP

COMMAND_NAME = "gitea-cli actions runner get"


def get_runner_command(
    ctx: typer.Context,
    runner_id: Annotated[int, typer.Option("--runner-id", help=RUNNER_ID_HELP)],
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
    """Get one Actions runner of a repository, an organization, an account or the instance.

    Args:
        ctx: The Typer context.
        runner_id: The ID of the runner.
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
        """Fetch the runner.

        Returns:
            A tuple containing the runner and metadata.

        """
        with reporting_scope_errors(COMMAND_NAME), Gitea(token=token, base_url=base_url) as client:
            return client.actions.get_runner(
                runner_id=runner_id,
                owner=owner,
                repository=repository,
                admin=admin,
            )

    execute_api_command(api_call=api_call, base_url=base_url, command_name=COMMAND_NAME)
