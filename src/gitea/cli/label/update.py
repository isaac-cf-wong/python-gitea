"""Update label command."""

from __future__ import annotations

from typing import Annotated

import typer

from gitea.cli.utils.options import REPOSITORY_REQUIRED_HELP


def update_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    label_id: Annotated[int, typer.Option("--label-id", help="ID of the label.")],
    repository: Annotated[str | None, typer.Option("--repository", help=REPOSITORY_REQUIRED_HELP)] = None,
    name: Annotated[
        str | None,
        typer.Option("--name", help="New name of the label."),
    ] = None,
    color: Annotated[
        str | None,
        typer.Option("--color", help="New color of the label in hexadecimal format."),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", help="New description of the label."),
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
    """Update a label in a repository.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository, which this command requires.
        label_id: The ID of the label.
        name: The new name of the label.
        color: The new color of the label in hexadecimal format.
        description: The new description of the label.
        account_name: Name of the account to use for authentication.
        token: Token for authentication.
        base_url: Base URL of the Gitea platform.

    """
    from typing import Any  # noqa: PLC0415

    from gitea.cli.utils.api import execute_api_command  # noqa: PLC0415
    from gitea.cli.utils.auth import get_auth_params  # noqa: PLC0415
    from gitea.cli.utils.options import require_repository  # noqa: PLC0415
    from gitea.client.gitea import Gitea  # noqa: PLC0415

    token, base_url = get_auth_params(
        config_path=ctx.obj.get("config_path"),
        account_name=account_name,
        token=token,
        base_url=base_url,
    )

    def api_call() -> tuple[dict[str, Any] | list[dict[str, Any]], dict[str, Any]]:
        """Update label information.

        Returns:
            A tuple containing the label data and metadata.

        """
        target_repository = require_repository(repository, command="gitea-cli label update")

        with Gitea(token=token, base_url=base_url) as client:
            return client.label.edit_label(
                owner=owner,
                repository=target_repository,
                label_id=label_id,
                name=name,
                color=color,
                description=description,
            )

    execute_api_command(api_call=api_call, base_url=base_url, command_name="gitea-cli label update")
