"""Rerun an Actions workflow run.

`--failed-jobs` reruns only the jobs that failed, which is a different endpoint
and the one to reach for when a long run failed on one flaky job: the jobs that
succeeded keep their results instead of being run again. It also answers without
a body, where rerunning the whole run answers with the run - so an empty payload
there is a rerun that started.

To rerun one named job rather than all the failed ones, use
`gitea-cli actions job rerun`.
"""

from __future__ import annotations

from typing import Annotated

import typer

from gitea.cli.utils.options import REPOSITORY_REQUIRED_HELP, RUN_ID_HELP

COMMAND_NAME = "gitea-cli actions run rerun"


def rerun_run_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    run_id: Annotated[int, typer.Option("--run-id", help=RUN_ID_HELP)],
    failed_jobs: Annotated[
        bool,
        typer.Option(
            "--failed-jobs",
            help="Rerun only the jobs of the run that failed, leaving the ones that succeeded as they are.",
        ),
    ] = False,
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
    """Rerun an Actions workflow run.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        run_id: The ID of the run.
        failed_jobs: Whether to rerun only the jobs that failed.
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
        """Rerun the run.

        Returns:
            A tuple containing the run the rerun is on - or an empty object,
            for the failed-jobs form, which answers without a body - and metadata.

        """
        target_repository = require_repository(repository, command=COMMAND_NAME)

        with Gitea(token=token, base_url=base_url) as client:
            return client.actions.rerun_workflow_run(
                owner=owner,
                repository=target_repository,
                run_id=run_id,
                failed_jobs_only=failed_jobs,
            )

    execute_api_command(api_call=api_call, base_url=base_url, command_name=COMMAND_NAME)
