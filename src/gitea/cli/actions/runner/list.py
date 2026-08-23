"""List the Actions runners of a repository, an organization, an account or the instance.

A runner is registered to one scope and then runs the jobs of everything under it,
so a scope's runners are the ones registered *there* - not every runner that could
pick up its jobs. A repository whose jobs all run on an organization runner has an
empty listing of its own, and that is not a repository with nowhere to run.

Which scope is asked for follows the usual convention - `--owner` with
`--repository` for a repository, `--owner` alone for an organization, neither for
the authenticated account - and `--admin` asks for the instance.

`status` on each entry says whether the runner is reachable and `busy` whether it
is running something. The two are independent of `--state`: a runner can be
online and disabled at once, and then takes no jobs at all.
"""

from __future__ import annotations

from typing import Annotated

import typer

from gitea.cli.actions.runner.state import RUNNER_STATE_HELP, RunnerState, is_disabled
from gitea.cli.utils.options import ADMIN_HELP, OWNER_SCOPE_HELP, REPOSITORY_SCOPE_HELP

COMMAND_NAME = "gitea-cli actions runner list"


def list_runners_command(
    ctx: typer.Context,
    owner: Annotated[str | None, typer.Option("--owner", help=OWNER_SCOPE_HELP)] = None,
    repository: Annotated[str | None, typer.Option("--repository", help=REPOSITORY_SCOPE_HELP)] = None,
    admin: Annotated[bool, typer.Option("--admin", help=ADMIN_HELP)] = False,
    state: Annotated[RunnerState | None, typer.Option("--state", help=RUNNER_STATE_HELP)] = None,
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
    """List the Actions runners of a repository, an organization, an account or the instance.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository, or the organization itself.
        repository: The name of the repository, to narrow the owner to one of its repositories.
        admin: Whether to address the whole instance.
        state: The state to list the runners of, or None to list both.
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
        """List the runners of the scope.

        Returns:
            A tuple containing the listing - an object carrying `total_count`
            and `runners`, as the endpoint answers with - and metadata.

        """
        disabled = is_disabled(state)

        with reporting_scope_errors(COMMAND_NAME), Gitea(token=token, base_url=base_url) as client:
            return client.actions.list_runners(
                owner=owner,
                repository=repository,
                admin=admin,
                disabled=disabled,
            )

    execute_api_command(api_call=api_call, base_url=base_url, command_name=COMMAND_NAME)
