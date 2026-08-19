"""Show a project together with its columns and the cards on them."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from gitea.utils.pagination import PAGE_SIZE, collect_all_pages


def show_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    project_id: Annotated[int, typer.Option("--project-id", help="ID of the project.")],
    full: Annotated[
        bool,
        typer.Option("--full", help="Include each column's issues in full, rather than their IDs alone."),
    ] = False,
    repository: Annotated[
        str | None,
        typer.Option("--repository", help="Name of the repository. Omit for organization projects."),
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
    """Show a project, its columns, and how many cards sit in each of them.

    `project get` answers with the project's own object, which says nothing
    about the board's shape: reading which cards sit where takes a call for the
    columns and another for each column's issues. This makes that one command.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository, or None for organization projects.
        project_id: The ID of the project.
        full: Whether to include each column's issues in full.
        account_name: Name of the account to use for authentication.
        token: Token for authentication.
        base_url: Base URL of the Gitea platform.

    """
    from gitea.cli.utils.api import execute_api_command  # noqa: PLC0415
    from gitea.cli.utils.auth import get_auth_params  # noqa: PLC0415
    from gitea.client.gitea import Gitea  # noqa: PLC0415

    token, base_url = get_auth_params(
        config_path=ctx.obj.get("config_path"),
        account_name=account_name,
        token=token,
        base_url=base_url,
    )

    def api_call() -> tuple[dict[str, Any] | list[dict[str, Any]], dict[str, Any]]:
        """Fetch the project, its columns, and the issues on each column.

        Every page of columns, and every page of each column's issues, is
        fetched, so the counts describe the whole board rather than its first
        page.

        Returns:
            A tuple containing the project with its columns, and metadata.

        """
        with Gitea(token=token, base_url=base_url) as client:
            project, metadata = client.project.get_project(
                owner=owner,
                repository=repository,
                project_id=project_id,
            )

            columns, _ = collect_all_pages(
                lambda page: client.project.list_project_columns(
                    owner=owner,
                    repository=repository,
                    project_id=project_id,
                    page=page,
                    limit=PAGE_SIZE,
                )
            )

            described: list[dict[str, Any]] = []
            issue_count = 0
            for column in columns:
                issues, _ = collect_all_pages(
                    lambda page, column_id=column["id"]: client.project.list_project_column_issues(
                        owner=owner,
                        repository=repository,
                        project_id=project_id,
                        column_id=column_id,
                        page=page,
                        limit=PAGE_SIZE,
                    )
                )
                issue_count += len(issues)
                described.append(_describe_column(column, issues, full=full))

        data = {"project": project, "columns": described}
        return data, {**metadata, "column_count": len(described), "issue_count": issue_count}

    execute_api_command(api_call=api_call, base_url=base_url, command_name="gitea-cli project show")


def _describe_column(column: dict[str, Any], issues: list[dict[str, Any]], *, full: bool) -> dict[str, Any]:
    """Describe one column of a board by the cards sitting on it.

    The column is the API's own object with the card fields added to it, rather
    than a rebuilt one: nothing the endpoint sent is dropped or renamed, and
    what is added is what the endpoint has no way of saying - how many issues
    are on the column, and which. A column payload that ever carried a field of
    one of these names would be overwritten here, which is the cost of adding
    them alongside rather than under a key of their own.

    Args:
        column: The column, as the API returned it.
        issues: Every issue on the column, across all of its pages.
        full: Whether to include the issues themselves, and not their IDs alone.

    Returns:
        The column with `issue_count` and `issue_ids` added, and `issues` too
        when the whole cards were asked for.

    """
    described = {**column, "issue_count": len(issues), "issue_ids": [issue["id"] for issue in issues]}
    if full:
        described["issues"] = issues
    return described
