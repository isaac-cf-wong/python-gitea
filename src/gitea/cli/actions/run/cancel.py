"""Cancel an Actions workflow run.

Cancelling asks the run's jobs to stop and waits for them to notice, which is
what a healthy run does within a few seconds. A job whose runner has gone away
never notices, and the run then sits in `in_progress` for as long as anyone
waits: `gitea-cli actions run force-cancel` is the way out of that, and is a
different endpoint rather than a retry of this one.

The run as it now stands is what comes back, so `status` says whether the
cancellation has taken effect yet.
"""

from __future__ import annotations

from typing import Annotated

import typer

from gitea.cli.utils.options import REPOSITORY_REQUIRED_HELP, RUN_ID_HELP

COMMAND_NAME = "gitea-cli actions run cancel"


def cancel_run_command(
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
    """Cancel an Actions workflow run.

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
        """Cancel the run.

        Returns:
            A tuple containing the run as it now stands and metadata.

        """
        target_repository = require_repository(repository, command=COMMAND_NAME)

        with Gitea(token=token, base_url=base_url) as client:
            return client.actions.cancel_workflow_run(
                owner=owner,
                repository=target_repository,
                run_id=run_id,
                # Said rather than left to the default, so that this command and
                # 'run force-cancel' read as the pair of endpoints they are.
                force=False,
            )

    execute_api_command(api_call=api_call, base_url=base_url, command_name=COMMAND_NAME)
