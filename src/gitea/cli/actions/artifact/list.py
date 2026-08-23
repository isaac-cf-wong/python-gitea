"""List the artifacts of a repository, or of one of its runs.

`--run-id` addresses the run's own artifacts, which is a different endpoint
rather than a filter on the repository-wide listing - the same shape as
`gitea-cli actions run list --workflow-id`.

An expired artifact is still listed: Gitea keeps the record after deleting the
archive, so `expired` is worth reading before asking for a download that would
answer with nothing.
"""

from __future__ import annotations

from typing import Annotated

import typer

from gitea.cli.utils.options import REPOSITORY_REQUIRED_HELP, RUN_ID_HELP

COMMAND_NAME = "gitea-cli actions artifact list"


def list_artifacts_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    repository: Annotated[str | None, typer.Option("--repository", help=REPOSITORY_REQUIRED_HELP)] = None,
    run_id: Annotated[int | None, typer.Option("--run-id", help=RUN_ID_HELP)] = None,
    name: Annotated[
        str | None,
        typer.Option(
            "--name", help="List the artifacts uploaded under this name alone. A run uploading one per job has several."
        ),
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
    """List the artifacts of a repository, or of one of its runs.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository, which this command requires.
        run_id: The ID of the run.
        name: The name to list the artifacts of.
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
        """List the artifacts.

        Returns:
            A tuple containing the listing - an object carrying `total_count`
            and `artifacts`, as the endpoint answers with - and metadata.

        """
        target_repository = require_repository(repository, command=COMMAND_NAME)

        with Gitea(token=token, base_url=base_url) as client:
            return client.actions.list_artifacts(
                owner=owner,
                repository=target_repository,
                run_id=run_id,
                name=name,
            )

    execute_api_command(api_call=api_call, base_url=base_url, command_name=COMMAND_NAME)
