"""Add issue to project column command."""

from __future__ import annotations

from typing import Annotated

import typer


def add_issue_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    project_id: Annotated[int, typer.Option("--project-id", help="ID of the project.")],
    column_id: Annotated[int, typer.Option("--column-id", help="ID of the column.")],
    issue_id: Annotated[
        int,
        typer.Option(
            "--issue-id",
            help="Issue number shown in the web UI, or the global ID of the issue when the repository holding it is unknown.",
        ),
    ],
    repository: Annotated[
        str | None,
        typer.Option("--repository", help="Name of the repository. Omit for organization projects."),
    ] = None,
    issue_repository: Annotated[
        str | None,
        typer.Option(
            "--issue-repository",
            help="Name of the repository holding the issue, so --issue-id can be its issue number. Defaults to --repository.",
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
    """Add an issue to a project column.

    This is what puts an issue on a board: 'project issue move' relocates a card
    the issue already has on the project, so it is this command that has to run
    first for an issue with none.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository, or None for organization projects.
        project_id: The ID of the project.
        column_id: The ID of the column.
        issue_id: The issue number of the repository holding the issue, or the
            global issue ID when that repository is not known.
        issue_repository: The name of the repository holding the issue,
            defaulting to the repository holding the project.
        account_name: Name of the account to use for authentication.
        token: Token for authentication.
        base_url: Base URL of the Gitea platform.

    """
    from typing import Any  # noqa: PLC0415

    from gitea.cli.utils.api import execute_api_command  # noqa: PLC0415
    from gitea.cli.utils.auth import get_auth_params  # noqa: PLC0415
    from gitea.cli.utils.issue import run_project_issue_call  # noqa: PLC0415
    from gitea.client.gitea import Gitea  # noqa: PLC0415

    token, base_url = get_auth_params(
        config_path=ctx.obj.get("config_path"),
        account_name=account_name,
        token=token,
        base_url=base_url,
    )

    def api_call() -> tuple[dict[str, Any] | list[dict[str, Any]], dict[str, Any]]:
        """Add issue to project column information.

        Returns:
            A tuple containing the response data and metadata.

        """
        with Gitea(token=token, base_url=base_url) as client:
            return run_project_issue_call(
                client=client,
                call=lambda resolved_issue_id: client.project.add_issue_to_project_column(
                    owner=owner,
                    repository=repository,
                    project_id=project_id,
                    column_id=column_id,
                    issue_id=resolved_issue_id,
                ),
                action="add",
                owner=owner,
                project_id=project_id,
                issue_number=issue_id,
                issue_repository=issue_repository or repository,
            )

    execute_api_command(api_call=api_call, base_url=base_url, command_name="gitea-cli project issue add")
