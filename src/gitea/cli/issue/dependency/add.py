"""Add issue dependency command."""

from __future__ import annotations

from typing import Annotated

import typer

from gitea.cli.utils.options import DEPRECATED_INDEX_HELP, ISSUE_ID_HELP, REPOSITORY_REQUIRED_HELP


def add_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    dependency_owner: Annotated[
        str,
        typer.Option("--dependency-owner", help="Owner of the dependency issue's repository."),
    ],
    dependency_repository: Annotated[
        str,
        typer.Option("--dependency-repository", help="Name of the dependency issue's repository."),
    ],
    repository: Annotated[str | None, typer.Option("--repository", help=REPOSITORY_REQUIRED_HELP)] = None,
    issue_id: Annotated[int | None, typer.Option("--issue-id", help=ISSUE_ID_HELP)] = None,
    index: Annotated[int | None, typer.Option("--index", help=DEPRECATED_INDEX_HELP, hidden=True)] = None,
    dependency_issue_id: Annotated[
        int | None,
        typer.Option("--dependency-issue-id", help="Issue number of the dependency issue, shown in the web UI."),
    ] = None,
    dependency_index: Annotated[
        int | None,
        typer.Option("--dependency-index", help="Deprecated alias of --dependency-issue-id.", hidden=True),
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
    """Make an issue depend on another issue.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository, which this command requires.
        issue_id: The issue number shown in the web UI.
        index: The deprecated name of `issue_id`.
        dependency_owner: The owner of the dependency issue's repository.
        dependency_repository: The name of the dependency issue's repository.
        dependency_issue_id: The issue number of the dependency issue.
        dependency_index: The deprecated name of `dependency_issue_id`.
        account_name: Name of the account to use for authentication.
        token: Token for authentication.
        base_url: Base URL of the Gitea platform.

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
        """Add issue dependency information.

        Returns:
            A tuple containing the target issue data and metadata.

        """
        target_repository = require_repository(repository, command="gitea-cli issue dependency add")
        target_issue = resolve_issue_id(issue_id=issue_id, index=index, command="gitea-cli issue dependency add")
        target_dependency_issue = resolve_issue_id(
            issue_id=dependency_issue_id,
            index=dependency_index,
            command="gitea-cli issue dependency add",
            option="--dependency-issue-id",
            deprecated_option="--dependency-index",
        )

        with Gitea(token=token, base_url=base_url) as client:
            return client.issue.create_issue_dependency(
                owner=owner,
                repository=target_repository,
                index=target_issue,
                dependency_owner=dependency_owner,
                dependency_repository=dependency_repository,
                dependency_index=target_dependency_issue,
            )

    execute_api_command(api_call=api_call, base_url=base_url, command_name="gitea-cli issue dependency add")
