"""Create milestone command."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

import typer


def create_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    repository: Annotated[str, typer.Option("--repository", help="Name of the repository.")],
    title: Annotated[str, typer.Option("--title", help="Title of the milestone.")],
    description: Annotated[
        str | None,
        typer.Option("--description", help="Description of the milestone."),
    ] = None,
    due_on: Annotated[
        datetime | None,
        typer.Option("--due-on", help="Due date of the milestone."),
    ] = None,
    state: Annotated[
        Literal["closed", "open"] | None,
        typer.Option("--state", help="State of the milestone."),
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
    """Create a milestone in a repository.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository.
        title: The title of the milestone.
        description: The description of the milestone.
        due_on: The due date of the milestone.
        state: The state of the milestone.
        account_name: Name of the account to use for authentication.
        token: Token for authentication.
        base_url: Base URL of the Gitea platform.

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
        """Create milestone information.

        Returns:
            A tuple containing the milestone data and metadata.

        """
        with Gitea(token=token, base_url=base_url) as client:
            return client.milestone.create_milestone(
                owner=owner,
                repository=repository,
                title=title,
                description=description,
                due_on=due_on,
                state=state,
            )

    execute_api_command(api_call=api_call, base_url=base_url, command_name="gitea-cli milestone create")
