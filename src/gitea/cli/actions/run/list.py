"""List the Actions workflow runs of a repository."""

from __future__ import annotations

from typing import Annotated

import typer

from gitea.cli.utils.options import REPOSITORY_REQUIRED_HELP, WORKFLOW_ID_HELP

COMMAND_NAME = "gitea-cli actions run list"

STATUS_HELP = "Status of the runs to list: pending, queued, in_progress, failure, success or skipped."


def list_runs_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    repository: Annotated[str | None, typer.Option("--repository", help=REPOSITORY_REQUIRED_HELP)] = None,
    workflow_id: Annotated[
        str | None,
        typer.Option("--workflow-id", help=f"List the runs of this workflow alone. {WORKFLOW_ID_HELP}"),
    ] = None,
    event: Annotated[
        str | None,
        typer.Option("--event", help="Event that triggered the run, e.g. push or workflow_dispatch."),
    ] = None,
    branch: Annotated[str | None, typer.Option("--branch", help="Branch the run is on.")] = None,
    status: Annotated[str | None, typer.Option("--status", help=STATUS_HELP)] = None,
    actor: Annotated[str | None, typer.Option("--actor", help="User who triggered the run.")] = None,
    head_sha: Annotated[str | None, typer.Option("--head-sha", help="Commit the run was triggered for.")] = None,
    exclude_pull_requests: Annotated[
        bool,
        typer.Option(
            "--exclude-pull-requests",
            help="Leave the pull_requests field of each run empty, which makes a long listing much smaller.",
        ),
    ] = False,
    page: Annotated[int | None, typer.Option("--page", help="The page number for pagination.")] = None,
    limit: Annotated[int | None, typer.Option("--limit", help="The number of runs per page.")] = None,
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
    """List the Actions workflow runs of a repository.

    The listing is the object the endpoint answers with: `total_count` and
    `workflow_runs`, rather than a bare array as the other listings in this CLI
    return. One page is fetched per invocation, so `--page` and `--limit` are
    how a caller walks a long history.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository, which this command requires.
        workflow_id: The file name of the workflow to list the runs of.
        event: The event that triggered the run.
        branch: The branch the run is on.
        status: The status of the runs to list.
        actor: The user who triggered the run.
        head_sha: The commit the run was triggered for.
        exclude_pull_requests: Whether to empty each run's pull_requests field.
        page: The page number for pagination.
        limit: The number of runs per page.
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
        """List the workflow runs.

        Returns:
            A tuple containing the run listing and metadata.

        """
        target_repository = require_repository(repository, command=COMMAND_NAME)

        with Gitea(token=token, base_url=base_url) as client:
            return client.actions.list_workflow_runs(
                owner=owner,
                repository=target_repository,
                workflow_id=workflow_id,
                event=event,
                branch=branch,
                status=status,
                actor=actor,
                head_sha=head_sha,
                # Asked for only when the flag is set, so a listing that did not
                # ask to drop the pull requests sends no such parameter at all.
                exclude_pull_requests=True if exclude_pull_requests else None,
                page=page,
                limit=limit,
            )

    execute_api_command(api_call=api_call, base_url=base_url, command_name=COMMAND_NAME)
