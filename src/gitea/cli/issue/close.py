"""Close issues command."""

from __future__ import annotations

from typing import Annotated

import typer

from gitea.cli.utils.options import DEPRECATED_INDEX_HELP, ISSUE_ID_HELP, REPOSITORY_REQUIRED_HELP


def close_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    repository: Annotated[str | None, typer.Option("--repository", help=REPOSITORY_REQUIRED_HELP)] = None,
    issue_id: Annotated[int | None, typer.Option("--issue-id", help=ISSUE_ID_HELP)] = None,
    index: Annotated[int | None, typer.Option("--index", help=DEPRECATED_INDEX_HELP, hidden=True)] = None,
    comment: Annotated[
        str | None,
        typer.Option("--comment", help="Body of a comment to post on the issue as it is closed."),
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
    """Close an issue in a repository.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository, which this command requires.
        issue_id: The issue number shown in the web UI.
        index: The deprecated name of `issue_id`.
        comment: The body of a comment to post on the issue as it is closed. No
            comment is posted when it is omitted.
        account_name: Name of the account to use for authentication.
        token: Token for authentication. If not provided, the token from the specified account will be used.
        base_url: Base URL of the Gitea platform. If not provided, the base URL from the specified account will be used.

    """
    from typing import Any  # noqa: PLC0415

    from gitea.cli.utils.api import execute_api_command  # noqa: PLC0415
    from gitea.cli.utils.auth import get_auth_params  # noqa: PLC0415
    from gitea.cli.utils.options import require_repository, resolve_issue_id  # noqa: PLC0415
    from gitea.client.gitea import Gitea  # noqa: PLC0415

    token, base_url = get_auth_params(
        config_path=ctx.obj.get("config_path"),
        account_name=account_name,
        token=token,
        base_url=base_url,
    )

    def api_call() -> tuple[dict[str, Any] | list[dict[str, Any]], dict[str, Any]]:
        """Close the issue, and comment on it when a comment was given.

        The issue is closed before the comment is posted, so a comment that
        cannot be posted leaves the issue closed rather than leaving the close
        undone. The result is the closed issue: the comment is what the command
        does on the way past, not what it was asked for.

        Returns:
            A tuple containing the issue data and metadata.

        """
        target_repository = require_repository(repository, command="gitea-cli issue close")
        target_issue = resolve_issue_id(issue_id=issue_id, index=index, command="gitea-cli issue close")

        with Gitea(token=token, base_url=base_url) as client:
            closed = client.issue.edit_issue(
                owner=owner,
                repository=target_repository,
                index=target_issue,
                state="closed",
            )

            if comment is not None:
                client.comment.create_comment(
                    owner=owner,
                    repository=target_repository,
                    index=target_issue,
                    body=comment,
                )

            return closed

    execute_api_command(api_call=api_call, base_url=base_url, command_name="gitea-cli issue close")
