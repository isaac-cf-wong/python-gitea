"""Move project issue command."""

from __future__ import annotations

from typing import Annotated

import typer


def move_issue_command(
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
    column_id: Annotated[int, typer.Option("--column-id", help="Target column ID.")],
    sorting: Annotated[
        int | None,
        typer.Option("--sorting", help="Position within the column, ascending."),
    ] = None,
    add_if_missing: Annotated[
        bool,
        typer.Option(
            "--add-if-missing",
            help="Put the issue in the target column when it has no card on the project yet, instead of failing.",
        ),
    ] = False,
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
    """Move an issue's card between a project's columns.

    The issue has to be on the project already: a move relocates the card the
    issue has there, and an issue with no card has nothing to relocate. Gitea
    answers such a call with a success all the same, so the card is looked for
    first and its absence is reported as an error naming 'project issue add',
    which is the command that puts an issue on a board. Pass --add-if-missing to
    have this command do that itself when there is no card yet.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository, or None for organization projects.
        project_id: The ID of the project.
        issue_id: The issue number of the repository holding the issue, or the
            global issue ID when that repository is not known.
        column_id: The target column ID.
        sorting: The position within the column, ascending.
        add_if_missing: Whether to put the issue in the target column when it has
            no card on the project yet, rather than reporting that it has none.
        issue_repository: The name of the repository holding the issue,
            defaulting to the repository holding the project.
        account_name: Name of the account to use for authentication.
        token: Token for authentication.
        base_url: Base URL of the Gitea platform.

    """
    from typing import Any  # noqa: PLC0415

    from gitea.cli.utils.api import execute_api_command  # noqa: PLC0415
    from gitea.cli.utils.auth import get_auth_params  # noqa: PLC0415
    from gitea.cli.utils.issue import run_project_issue_move  # noqa: PLC0415
    from gitea.client.gitea import Gitea  # noqa: PLC0415

    token, base_url = get_auth_params(
        config_path=ctx.obj.get("config_path"),
        account_name=account_name,
        token=token,
        base_url=base_url,
    )

    def api_call() -> tuple[dict[str, Any] | list[dict[str, Any]], dict[str, Any]]:
        """Move project issue information.

        Returns:
            A tuple containing the response data and metadata.

        """
        with Gitea(token=token, base_url=base_url) as client:
            return run_project_issue_move(
                client=client,
                owner=owner,
                repository=repository,
                project_id=project_id,
                issue_number=issue_id,
                column_id=column_id,
                sorting=sorting,
                issue_repository=issue_repository or repository,
                add_if_missing=add_if_missing,
            )

    execute_api_command(api_call=api_call, base_url=base_url, command_name="gitea-cli project issue move")
