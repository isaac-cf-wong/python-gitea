"""Get issues command."""

from __future__ import annotations

from typing import Annotated, Any

import typer


def rename_comment_count(issue: dict[str, Any]) -> dict[str, Any]:
    """Rename the ``comments`` field of an issue to ``comment_count``.

    The Gitea API returns ``comments`` as an integer count rather than the list of
    comments, which misleads consumers expecting comment bodies. The value is kept
    as-is; only the name is made unambiguous. Use ``gitea-cli issue comment list``
    (or ``gitea-cli comment list``) to retrieve the comments themselves.

    Args:
        issue: The issue data returned by the API.

    Returns:
        The issue data with ``comments`` renamed to ``comment_count``.

    """
    if "comments" not in issue:
        return issue
    return {("comment_count" if key == "comments" else key): value for key, value in issue.items()}


def get_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    repository: Annotated[str, typer.Option("--repository", help="Name of the repository.")],
    index: Annotated[int, typer.Option("--index", help="Index of the issue.")],
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
    """Get a specific issue in a repository.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository.
        index: The index of the issue.
        account_name: Name of the account to use for authentication.
        token: Token for authentication. If not provided, the token from the specified account will be used.
        base_url: Base URL of the Gitea platform. If not provided, the base URL from the specified account will be used.

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

    def api_call() -> tuple[dict[str, Any], dict[str, Any]]:
        """Get issue information.

        Returns:
            A tuple containing the issue data and metadata.

        """
        with Gitea(token=token, base_url=base_url) as client:
            data, metadata = client.issue.get_issue(
                owner=owner,
                repository=repository,
                index=index,
            )
        return rename_comment_count(data), metadata

    execute_api_command(api_call=api_call, command_name="gitea-cli issue get")
