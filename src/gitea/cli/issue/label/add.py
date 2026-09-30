"""Add issue labels command."""

from __future__ import annotations

from typing import Annotated

import typer

from gitea.cli.issue.label.common import ISSUE_IDS_HELP, LABEL_HELP
from gitea.cli.utils.options import REPOSITORY_REQUIRED_HELP


def add_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    repository: Annotated[str | None, typer.Option("--repository", help=REPOSITORY_REQUIRED_HELP)] = None,
    issue_ids: Annotated[list[int] | None, typer.Option("--issue-id", help=ISSUE_IDS_HELP)] = None,
    labels: Annotated[list[str] | None, typer.Option("--label", help=LABEL_HELP)] = None,
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
    """Add labels to one or more issues, keeping the labels they already have.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository, which this command requires.
        issue_ids: The issue numbers shown in the web UI.
        labels: The labels, each a name or a numeric ID.
        account_name: Name of the account to use for authentication.
        token: Token for authentication.
        base_url: Base URL of the Gitea platform.

    """
    from typing import Any  # noqa: PLC0415

    from gitea.cli.issue.label.common import (  # noqa: PLC0415
        for_each_issue,
        require_issue_ids,
        require_labels,
        resolve_label_ids,
    )
    from gitea.cli.utils.api import execute_api_command  # noqa: PLC0415
    from gitea.cli.utils.auth import get_auth_params  # noqa: PLC0415
    from gitea.cli.utils.options import require_repository  # noqa: PLC0415
    from gitea.client.gitea import Gitea  # noqa: PLC0415

    command = "gitea-cli issue label add"
    token, base_url = get_auth_params(
        config_path=ctx.obj.get("config_path"),
        account_name=account_name,
        token=token,
        base_url=base_url,
    )

    def api_call() -> tuple[dict[str, Any] | list[dict[str, Any]], dict[str, Any]]:
        """Add the labels to each issue.

        Returns:
            A tuple containing the issue's resulting labels, or one entry per issue, and metadata.

        """
        target_repository = require_repository(repository, command=command)
        targets = require_issue_ids(issue_ids, command=command)
        requested = require_labels(labels, command=command)

        with Gitea(token=token, base_url=base_url) as client:
            label_ids = resolve_label_ids(client, owner, target_repository, requested, command=command)
            # POST appends to the issue's labels; PUT would replace them.
            return for_each_issue(
                targets,
                lambda issue_id: client.issue.add_issue_labels(
                    owner=owner, repository=target_repository, index=issue_id, labels=list(label_ids)
                ),
                command=command,
            )

    execute_api_command(api_call=api_call, base_url=base_url, command_name=command)
