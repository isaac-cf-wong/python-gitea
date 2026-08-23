"""Approve an Actions workflow run that is waiting for approval.

A run triggered by a first-time contributor's pull request waits for someone with
write access before any of it executes, and shows as `blocked` until then. This
is that approval. A run that was not waiting for one is reported as a conflict
rather than approved twice.
"""

from __future__ import annotations

from typing import Annotated

import typer

from gitea.cli.utils.options import REPOSITORY_REQUIRED_HELP, RUN_ID_HELP

COMMAND_NAME = "gitea-cli actions run approve"


def approve_run_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    run_id: Annotated[int, typer.Option("--run-id", help=RUN_ID_HELP)],
    repository: Annotated[str | None, typer.Option("--repository", help=REPOSITORY_REQUIRED_HELP)] = None,
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
    """Approve an Actions workflow run that is waiting for approval.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        run_id: The ID of the run.
        repository: The name of the repository, which this command requires.
        account_name: Name of the account to use for authentication.
        token: Token for authentication.
        base_url: Base URL of the Gitea platform.

    """
    from typing import Any  # noqa: PLC0415

    from gitea.cli.utils.api import execute_api_command  # noqa: PLC0415
    from gitea.cli.utils.auth import get_auth_params  # noqa: PLC0415
    from gitea.cli.utils.options import require_repository  # noqa: PLC0415
    from gitea.client.gitea import Gitea  # noqa: PLC0415

    token, base_url = get_auth_params(
        config_path=ctx.obj.get("config_path"),
        account_name=account_name,
        token=token,
        base_url=base_url,
    )

    def api_call() -> tuple[dict[str, Any] | list[dict[str, Any]], dict[str, Any]]:
        """Approve the run.

        Returns:
            A tuple containing the run as it now stands and metadata.

        """
        target_repository = require_repository(repository, command=COMMAND_NAME)

        with Gitea(token=token, base_url=base_url) as client:
            return client.actions.approve_workflow_run(
                owner=owner,
                repository=target_repository,
                run_id=run_id,
            )

    execute_api_command(api_call=api_call, base_url=base_url, command_name=COMMAND_NAME)
