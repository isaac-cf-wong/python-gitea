"""List the Actions jobs of a repository, an organization, an account or the instance.

This is a different endpoint from `gitea-cli actions run jobs`, and the
difference is what makes it useful: it answers with every job of the scope rather
than the jobs of one run, so `--status queued` finds the jobs that are waiting
for a runner without walking the runs to reach them.

Which scope is asked for follows the usual convention - `--owner` with
`--repository` for a repository, `--owner` alone for an organization, neither for
the authenticated account - and `--admin` asks for the instance.
"""

from __future__ import annotations

from typing import Annotated

import typer

from gitea.cli.utils.options import ADMIN_HELP, OWNER_SCOPE_HELP, REPOSITORY_SCOPE_HELP

COMMAND_NAME = "gitea-cli actions job list"


def list_jobs_command(
    ctx: typer.Context,
    owner: Annotated[str | None, typer.Option("--owner", help=OWNER_SCOPE_HELP)] = None,
    repository: Annotated[str | None, typer.Option("--repository", help=REPOSITORY_SCOPE_HELP)] = None,
    admin: Annotated[bool, typer.Option("--admin", help=ADMIN_HELP)] = False,
    status: Annotated[
        str | None,
        typer.Option(
            "--status", help="Status of the jobs to list: pending, queued, in_progress, failure, success or skipped."
        ),
    ] = None,
    page: Annotated[int | None, typer.Option("--page", help="The page number for pagination.")] = None,
    limit: Annotated[int | None, typer.Option("--limit", help="The number of jobs per page.")] = None,
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
    """List the Actions jobs of a repository, an organization, an account or the instance.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository, or the organization itself.
        repository: The name of the repository, to narrow the owner to one of its repositories.
        admin: Whether to address the whole instance.
        status: The status of the jobs to list.
        page: The page number for pagination.
        limit: The number of jobs per page.
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
        """List the jobs of the scope.

        Returns:
            A tuple containing the listing - an object carrying `total_count`
            and `jobs`, as the endpoint answers with - and metadata.

        """
        with reporting_scope_errors(COMMAND_NAME), Gitea(token=token, base_url=base_url) as client:
            return client.actions.list_workflow_jobs(
                owner=owner,
                repository=repository,
                admin=admin,
                status=status,
                page=page,
                limit=limit,
            )

    execute_api_command(api_call=api_call, base_url=base_url, command_name=COMMAND_NAME)
