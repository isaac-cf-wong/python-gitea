"""List pull requests command."""

from __future__ import annotations

from typing import Annotated, Literal

import typer


def list_command(  # noqa: PLR0913
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    repository: Annotated[str, typer.Option("--repository", help="Name of the repository.")],
    base_branch: Annotated[
        str | None,
        typer.Option("--base-branch", help="Filter pull requests by base branch."),
    ] = None,
    state: Annotated[
        Literal["open", "closed", "all"] | None,
        typer.Option("--state", help="Filter pull requests by state."),
    ] = None,
    sort: Annotated[
        Literal["oldest", "recentupdate", "recentclose", "leastupdate", "mostcomment", "leastcomment", "priority"]
        | None,
        typer.Option("--sort", help="Sort pull requests by the given criteria."),
    ] = None,
    milestone: Annotated[
        int | None,
        typer.Option("--milestone", help="Filter pull requests by milestone."),
    ] = None,
    labels: Annotated[
        list[int] | None,
        typer.Option("--labels", help="Filter pull requests by labels."),
    ] = None,
    poster: Annotated[
        str | None,
        typer.Option("--poster", help="Filter pull requests by poster."),
    ] = None,
    page: Annotated[
        int | None,
        typer.Option("--page", help="The page number for pagination."),
    ] = None,
    limit: Annotated[
        int | None,
        typer.Option("--limit", help="The number of pull requests per page."),
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
):
    """List pull requests in a repository.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository.
        base_branch: Filter pull requests by base branch.
        state: Filter pull requests by state.
        sort: Sort pull requests by the given criteria.
        milestone: Filter pull requests by milestone.
        labels: Filter pull requests by labels.
        poster: Filter pull requests by poster.
        page: The page number for pagination.
        limit: The number of pull requests per page.
        account_name: Name of the account to use for authentication.
        token: Token for authentication. If not provided, the token from the specified account will be used.
        base_url: Base URL of the Gitea platform. If not provided, the base URL from the specified account will be used.

    """
    from typing import Any  # noqa: PLC0415

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
        """List pull requests information."""
        with Gitea(token=token, base_url=base_url) as client:
            return client.pull_request.list_pull_requests(
                owner=owner,
                repository=repository,
                base_branch=base_branch,
                state=state,
                sort=sort,
                milestone=milestone,
                labels=labels,
                poster=poster,
                page=page,
                limit=limit,
            )

    execute_api_command(api_call=api_call, command_name="gitea-cli pull-request list")
