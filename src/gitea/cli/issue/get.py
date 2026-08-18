"""Get issues command.

The issue is emitted with the field names the API sends, as `gitea.utils.fields`
requires. `comments` is one worth knowing about: it is the *number* of comments
on the issue and not their bodies, which `gitea-cli issue comment list` is for.
An earlier version of this command renamed it to `comment_count` to say so, and
was the only command emitting an issue that did - the same count arrived under
two names depending on which command fetched the issue, which was the worse
surprise of the two.
"""

from __future__ import annotations

from typing import Annotated, Any

import typer

from gitea.cli.utils.options import DEPRECATED_INDEX_HELP, ISSUE_ID_HELP, REPOSITORY_REQUIRED_HELP


def get_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    repository: Annotated[str | None, typer.Option("--repository", help=REPOSITORY_REQUIRED_HELP)] = None,
    issue_id: Annotated[int | None, typer.Option("--issue-id", help=ISSUE_ID_HELP)] = None,
    index: Annotated[int | None, typer.Option("--index", help=DEPRECATED_INDEX_HELP, hidden=True)] = None,
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
        repository: The name of the repository, which this command requires.
        issue_id: The issue number shown in the web UI.
        index: The deprecated name of `issue_id`.
        account_name: Name of the account to use for authentication.
        token: Token for authentication. If not provided, the token from the specified account will be used.
        base_url: Base URL of the Gitea platform. If not provided, the base URL from the specified account will be used.

    """
    from gitea.cli.utils.api import execute_api_command  # noqa: PLC0415
    from gitea.cli.utils.auth import get_auth_params  # noqa: PLC0415
    from gitea.cli.utils.options import require_repository, resolve_issue_id  # noqa: PLC0415
    from gitea.client.gitea import Gitea  # noqa: PLC0415
    from gitea.issue.project_column import resolve_project_column_ids  # noqa: PLC0415

    token, base_url = get_auth_params(
        config_path=ctx.obj.get("config_path"),
        account_name=account_name,
        token=token,
        base_url=base_url,
    )

    def api_call() -> tuple[dict[str, Any], dict[str, Any]]:
        """Get issue information.

        The column of each project the issue is on is resolved from the project's
        board, because the issue payload names the projects without saying where
        on them the issue's card sits.

        Returns:
            A tuple containing the issue data and metadata.

        """
        target_repository = require_repository(repository, command="gitea-cli issue get")
        target_issue = resolve_issue_id(issue_id=issue_id, index=index, command="gitea-cli issue get")

        with Gitea(token=token, base_url=base_url) as client:
            data, metadata = client.issue.get_issue(
                owner=owner,
                repository=target_repository,
                index=target_issue,
            )
            data = resolve_project_column_ids(client=client, owner=owner, repository=target_repository, issue=data)
        return data, metadata

    execute_api_command(api_call=api_call, base_url=base_url, command_name="gitea-cli issue get")
