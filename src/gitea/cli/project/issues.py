"""List all issues on a project, grouped by column."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any

import typer

# Number of items requested per page when paging through a project's board.
PAGE_SIZE = 50


def _collect_all_pages(
    fetch_page: Callable[[int], tuple[list[dict[str, Any]], dict[str, Any]]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch every page of a paginated listing.

    Pages are requested until one comes back empty or shorter than the pages
    before it. The page size is taken from the first page rather than from the
    requested limit, because a Gitea instance may cap the page size below it.

    Args:
        fetch_page: Callable returning the items and metadata of the given page number.

    Returns:
        A tuple containing every item across all pages and the metadata of the last response.

    """
    items: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {}
    page = 1
    page_size = 0
    while True:
        batch, metadata = fetch_page(page)
        items.extend(batch)
        if not batch or len(batch) < page_size:
            return items, metadata
        page_size = max(page_size, len(batch))
        page += 1


def list_project_issues_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    project_id: Annotated[int, typer.Option("--project-id", help="ID of the project.")],
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
    """List every issue on a project, grouped by the column it sits in.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository, or None for organization projects.
        project_id: The ID of the project.
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
        """List the issues on every column of a project.

        Every page of columns, and every page of each column's issues, is fetched.

        Returns:
            A tuple containing one entry per column, each with its issues, and metadata.

        """
        with Gitea(token=token, base_url=base_url) as client:
            columns, metadata = _collect_all_pages(
                lambda page: client.project.list_project_columns(
                    owner=owner,
                    repository=repository,
                    project_id=project_id,
                    page=page,
                    limit=PAGE_SIZE,
                )
            )

            data: list[dict[str, Any]] = []
            issue_count = 0
            for column in columns:
                issues, _ = _collect_all_pages(
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
                data.append(
                    {
                        "column": {"id": column["id"], "title": column.get("title")},
                        "issues": issues,
                    }
                )

        return data, {**metadata, "column_count": len(data), "issue_count": issue_count}

    execute_api_command(api_call=api_call, command_name="gitea-cli project issues")
