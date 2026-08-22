"""Remove issue from project column command."""

from __future__ import annotations

from typing import Annotated

import typer


def remove_issue_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    project_id: Annotated[int, typer.Option("--project-id", help="ID of the project.")],
    issue_id: Annotated[
        int,
        typer.Option(
            "--issue-id",
            help="Issue number shown in the web UI, or the global ID of the issue when the repository holding it is unknown.",
        ),
    ],
    column_id: Annotated[
        int | None,
        typer.Option(
            "--column-id",
            help=(
                "ID of the column holding the issue's card. Omit to have the column found on the board, unlike "
                "'add' and 'move', whose --column-id is the column the card is going to."
            ),
        ),
    ] = None,
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
    """Take an issue's card off a project.

    --column-id is the column holding the card, which is where the two other
    'project issue' commands differ from this one: theirs is the column the card
    is going to, and is therefore something only the caller can say, while this
    one is where the card already is, and is something the board can be asked.
    Omit it and the project's columns are walked to find the card; an issue with
    no card on the project is reported as having none, and the column that was
    found comes back as metadata.resolved_column_id. Pass it and it is used as
    given - a column that does not hold the card is a removal Gitea answers with
    a success, having removed nothing.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository, or None for organization projects.
        project_id: The ID of the project.
        column_id: The ID of the column holding the card, or None to find it by
            walking the project's columns.
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
    from gitea.cli.utils.issue import run_project_issue_remove  # noqa: PLC0415
    from gitea.client.gitea import Gitea  # noqa: PLC0415

    token, base_url = get_auth_params(
        config_path=ctx.obj.get("config_path"),
        account_name=account_name,
        token=token,
        base_url=base_url,
    )

    def api_call() -> tuple[dict[str, Any] | list[dict[str, Any]], dict[str, Any]]:
        """Remove issue from project column information.

        Returns:
            A tuple containing the response data and metadata.

        """
        with Gitea(token=token, base_url=base_url) as client:
            return run_project_issue_remove(
                client=client,
                owner=owner,
                repository=repository,
                project_id=project_id,
                issue_number=issue_id,
                column_id=column_id,
                issue_repository=issue_repository or repository,
            )

    execute_api_command(api_call=api_call, base_url=base_url, command_name="gitea-cli project issue remove")
